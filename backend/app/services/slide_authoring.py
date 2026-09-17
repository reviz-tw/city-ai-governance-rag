"""Explicitly load the versioned slide skill for planning, composition and bounded review."""
import hashlib
import json
from pathlib import Path
from pydantic import ValidationError
from app.models.artifacts import ArtifactDraft, DeckOutline, SlideDeckDraft, SlideReview
from app.services import gemini
from app.services.languages import LANG_NAMES

SKILL_DIR = Path(__file__).resolve().parents[1] / 'skills' / 'research-slides'


class SlideQualityError(ValueError):
    """A safe diagnostic category without source text or model output."""
    def __init__(self, stage):
        self.stage = stage
        super().__init__(f'Slide quality checks failed after one repair ({stage})')


def instructions():
    return '\n\n'.join((SKILL_DIR / name).read_text(encoding='utf-8')
                       for name in ('SKILL.md', 'references/examples.md'))


def version():
    return 'research-slides-' + hashlib.sha256(instructions().encode()).hexdigest()[:12]


def validate_outline(outline, blocks, pages):
    known = {(b['document_id'], b['id']) for b in blocks}
    if len(outline.slides) > pages or (len(outline.slides) < pages and not outline.coverage_note.strip()):
        raise ValueError('Use the requested total page count, or explain an evidence-based reduction')
    if any((ref.document_id, ref.block_id) not in known for slide in outline.slides for ref in slide.citations):
        raise ValueError('Outline cites evidence outside the selected answer')


def generate(request, blocks, validate, progress):
    rules = instructions() + f'\nOutput language: {LANG_NAMES[request.language]}. Return the requested JSON schema.'
    context = dict(evidence=blocks, selected_answer=request.context, audience=request.audience,
                   desired_pages=request.pages)
    progress(10)
    outline = DeckOutline.model_validate_json(gemini.generate(json.dumps(context, ensure_ascii=False),
        rules + '\nPLAN: produce only the storyboard, with distinct purposes and supporting citations.', DeckOutline))
    validate_outline(outline, blocks, request.pages)
    progress(30)
    content = json.dumps({**context, 'outline':outline.model_dump()}, ensure_ascii=False)
    raw = gemini.generate(content, rules + '\nCOMPOSE: expand this outline into presentation-ready slides. '
        'Preserve the approved scope and evidence. Summary is deck metadata, not an extra slide.', SlideDeckDraft)
    for attempt in range(2):
        progress(50 + attempt*25)
        stage = 'content_structure'
        try:
            deck = SlideDeckDraft.model_validate_json(raw)
            if len(deck.slides) > request.pages or (len(deck.slides) < request.pages and not deck.coverage_note.strip()):
                raise ValueError('Respect the total page budget; explain a reduction with coverage_note')
            draft = ArtifactDraft.model_validate(deck.model_dump())
            stage = 'source_validation'
            validate(draft)
            stage = 'source_review'
            review = SlideReview.model_validate_json(gemini.generate(json.dumps({**context, 'draft':deck.model_dump()}, ensure_ascii=False),
                rules + '\nREVIEW: inspect source support, qualifications, audience usefulness and unnecessary repetition. '
                'Assess EVERY slide and its notes, especially the strength of obligations and assumptions in comparisons. '
                'Accept justified shorter decks. Return per-slide verdicts and specific defects that need correction.', SlideReview))
            if sorted(s.slide_number for s in review.slides) != list(range(1,len(deck.slides)+1)):
                raise ValueError('Review must assess every slide exactly once')
            issues = review.issues + [f'Slide {s.slide_number}: {s.assessment}' for s in review.slides if not s.supported]
            if not issues:
                return draft
        except ValidationError as exc:
            issues = []
            for error in exc.errors(include_input=False,include_context=False)[:12]:
                location = error['loc']
                field = (f'Slide {location[1]+1} (one-based), '+'.'.join(map(str,location[2:]))) if len(location)>1 and location[0]=='slides' and isinstance(location[1],int) else '.'.join(map(str,location))
                issues.append(f'{field}: {error["msg"]}')
        except ValueError as exc:
            if 'readable slide area' in str(exc) or 'Shorten chart category' in str(exc):
                stage = 'text_layout'
            issues = [str(exc)]
        if attempt:
            raise SlideQualityError(stage)
        progress(65)
        raw = gemini.generate(json.dumps({**context, 'outline':outline.model_dump(), 'draft_to_repair':raw, 'issues':issues}, ensure_ascii=False),
            rules + '\nREPAIR: correct the listed defects, preserve verified facts and return the complete revised deck.', SlideDeckDraft)
    raise ValueError('Slide authoring did not complete')
