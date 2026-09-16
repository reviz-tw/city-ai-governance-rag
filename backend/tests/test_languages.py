import pytest
from pydantic import ValidationError
from app.services.languages import resolve, normalize_language, source_languages
from app.models.schema import ChatStreamRequest

@pytest.mark.parametrize('question,language',[
    ('如何評估城市導入生成式人工智慧的風險？','zh-TW'),
    ('What risks should cities assess before using generative AI?','en'),
    ('都市の人工知能政策について説明してください。','ja'),
    ('Wie können Städte die Privatsphäre ihrer Bürger schützen?','de'),
    ('城市應該如何管理 AI governance 的透明度？','zh-TW'),
    ('Quels sont les risques de confidentialité pour les citoyens ?','fr'),
    ('¿Cómo pueden las ciudades proteger los datos personales?','es'),
    ('Как города могут защитить персональные данные граждан?','ru'),
])
def test_auto(question,language):
    result=resolve(question, interface_language='en')
    assert result.language==language
    assert result.source=='detected'

@pytest.mark.parametrize('question',['1999','Gemini','AI','123456789'])
def test_short_fallback(question):
    assert resolve(question,interface_language='ja').language=='ja'
    assert resolve(question,recent_languages=['fr','fr','en']).language=='fr'

@pytest.mark.parametrize('question,expected',[
    ('請用英文回答：城市有哪些風險？','en'),
    ('Answer in German. How should cities govern AI?','de'),
    ('日本語で回答してください。','ja'),
    ('Reply in French about city governance.','fr'),
    ('請用繁體中文回答','zh-TW'),
])
def test_explicit_instruction(question,expected):
    assert resolve(question, preferred_language='fr').language==expected
    assert resolve(question, response_language='es').language=='es'


def test_quoted_and_negative_directive_not_applied():
    assert resolve('不要用英文回答，請說明城市治理的透明度').language=='zh-TW'
    assert resolve('分析「請用英文回答」這句話的意思和政策脈絡').language=='zh-TW'


def test_code_validation():
    assert normalize_language('en-US')=='en'
    assert normalize_language('zh_Hant')=='zh-TW'
    assert source_languages(['en','EN-us','zh'])==['en','zh-TW']
    with pytest.raises(ValueError): normalize_language('en\") OR true')
    with pytest.raises(ValidationError): ChatStreamRequest(query='q',response_language='invalid')
    request=ChatStreamRequest(query='q',language='ja')
    assert request.response_language=='ja' and request.source_languages==[]

    with pytest.raises(ValidationError): ChatStreamRequest(query='q', response_language='ar')
    with pytest.raises(ValidationError): ChatStreamRequest(query='q', source_languages=['ar'])
    from app.models.artifacts import ArtifactRequest
    with pytest.raises(ValidationError): ArtifactRequest(kind='translation', language='ar')
