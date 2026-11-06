"""Deterministic numeric equivalence for translations; no model or database imports."""
import re
import unicodedata
from collections import Counter
from decimal import Decimal

LINKS = re.compile(r'https?://[^\s<>()]+')


def chinese_integer(value):
    """Parse an explicitly delimited Chinese list number, not arbitrary prose."""
    value = value.translate(str.maketrans('壹貳參肆伍陸柒捌玖拾佰仟','一二三四五六七八九十百千'))
    digits = dict(zip('零〇一二兩三四五六七八九', [0,0,1,2,2,3,4,5,6,7,8,9]))
    units = {'十':10, '百':100, '千':1000}
    if not any(c in units for c in value):
        return int(''.join(str(digits[c]) for c in value))
    total, digit = 0, 0
    for char in value:
        if char in units:
            total += (digit or 1) * units[char]
            digit = 0
        else:
            digit = digits[char]
    return total + digit


def normalize_list_numbers(text):
    # A documented false positive: 「（三）技術自主」 -> "(3) Technological...".
    # Restrict conversion to explicit enumeration markers. Words such as 一般
    # and 三重 remain prose and must not manufacture extra numeric facts.
    numeral = r'[零〇一二兩三四五六七八九十百千壹貳參肆伍陸柒捌玖拾佰仟]+'
    text = re.sub(r'(?m)^(\s*(?:#{1,6}\s*)?)\(('+numeral+r')\)',
                  lambda m:m[1]+'('+str(chinese_integer(m[2]))+')',text)
    return re.sub(r'(?m)^(\s*(?:#{1,6}\s*)?)('+numeral+r')[、.]',
                  lambda m:m[1]+str(chinese_integer(m[2]))+'.',text)


def normalize_roc_years(text, language):
    if language != 'zh-TW':
        return text
    # Only explicit ROC dates, Taiwanese annual-plan notation, or government
    # bibliography years. Never add 1911 to arbitrary counts or numbered items.
    citation = r'(?m)((?:政府文件|專案資訊)\s*[:：][^\n()]{2,120})\((\d{2,3})\)(?=[。.]\s*《)'
    years = {m[2] for m in re.finditer(citation,text)}
    text = re.sub(citation,lambda m:m[1]+'('+str(int(m[2])+1911)+')',text)
    # A dated government/project bibliography also supplies the calendar for
    # the same year in its title (e.g. （113）。《113年機關實證主題》).
    text = re.sub(r'(?<!\d)(\d{2,3})(?=\s*年)',
                  lambda m:str(int(m[1])+1911) if m[1] in years else m[1],text)
    text = re.sub(r'民國\s*(\d{1,3})\s*年',lambda m:str(int(m[1])+1911)+'年',text)
    text = re.sub(r'([於自])\s*(\d{2,3})\s*年(?=\s*(?:成立|設立|起|完成))',
                  lambda m:m[1]+str(int(m[2])+1911)+'年',text)
    text = re.sub(r'(?<!\d)(\d{2,3})(?=\s*年度)',lambda m:str(int(m[1])+1911),text)
    return text


def normalize_english_dates(text, language):
    if language != 'en':
        return text
    months = 'January February March April May June July August September October November December'.split()
    for number, month in enumerate(months,1):
        name = '(?:'+month+'|'+month[:3]+r'\.?)'
        day = r'(?:0?[1-9]|[12]\d|3[01])(?:st|nd|rd|th)?'
        text = re.sub(r'\b'+name+r'\s+('+day+r')\b',lambda m:str(number)+' '+m[1],text,flags=re.I)
        text = re.sub(r'\b('+day+r')\s+'+name+r'\b',lambda m:m[1]+' '+str(number),text,flags=re.I)
    def clock(m):
        hour = int(m[1]) % 12 + (12 if m[3].lower().startswith('p') else 0)
        return f'{hour}:{m[2]}'
    return re.sub(r'\b(1[0-2]|0?[1-9]):([0-5]\d)\s*([ap]\.?m\.?)\b',clock,text,flags=re.I)


def normalize_quantities(text, language):
    if language in {'zh-TW','zh-CN','ja'}:
        digit = r'[一二兩三四五六七八九]'
        # Colloquial ranges share a unit: 一兩千萬 means 10–20 million, not
        # twelve million. Preserve both endpoints before exact-number parsing.
        def bounds(m):
            a,b = chinese_integer(m[1]),chinese_integer(m[2])
            if b != a+1:
                return m[0]
            scale = {'成':10,'萬':10000,'億':100000000,'千萬':10000000,
                     '百萬':1000000,'千':1000,'百':100}[m[3]]
            return f'{a*scale} 到 {b*scale}'
        text = re.sub('('+digit+')('+digit+r')(千萬|百萬|萬|億|千|百|成)',bounds,text)
        text = re.sub('('+digit+r')成',lambda m:str(chinese_integer(m[1])*10),text)
        numeral = r'[零〇一二兩三四五六七八九十百千]+'
        text = re.sub(r'(?<![幾數数零〇一二兩三四五六七八九十百千])('+numeral+r')([萬万億亿])',
                      lambda m:str(chinese_integer(m[1]))+m[2],text)
    elif language == 'en':
        # "10 to 20 million" applies the same magnitude to both endpoints.
        text = re.sub(r'\b(\d+(?:[.,]\d+)?)\s*(?:to|[–—-])\s*(\d+(?:[.,]\d+)?)\s*(million|billion|thousand)\b',
                      lambda m:m[1]+' '+m[3]+' to '+m[2]+' '+m[3],text,flags=re.I)
    return text


def numeric_values(text, language='en'):
    """Normalize grouping, decimal separators and explicit magnitude units, not changed facts."""
    text = unicodedata.normalize('NFKC', LINKS.sub('', text))
    if language in {'zh-TW','zh-CN','ja'}:
        text = normalize_list_numbers(text)
    text = normalize_roc_years(text, language)
    text = normalize_english_dates(text, language)
    text = normalize_quantities(text, language)
    # Decimal comma languages must not interpret 1,234 as one thousand.
    comma_decimal = language in {'fr','es','ru','de'}
    grouping = r'[. \u00a0\u202f]' if comma_decimal else r'[, \u00a0\u202f]'
    text = re.sub(r'(?<=\d)'+grouping+r'(?=\d{3}(?:\D|$))', '', text)
    pattern = r'\d+(?:[.,]\d+)?(?:\s*(?:萬|万|億|亿|million\b|billion\b|thousand\b))?'
    values = []
    scales = {'萬':10000,'万':10000,'億':100000000,'亿':100000000,'million':1000000,'billion':1000000000,'thousand':1000}
    for token in re.findall(pattern, text, flags=re.I):
        number = re.match(r'\d+(?:[.,]\d+)?', token)[0]
        unit = token[len(number):].strip().lower()
        values.append(Decimal(number.replace(',', '.')) * scales.get(unit, 1))
    return Counter(values)

