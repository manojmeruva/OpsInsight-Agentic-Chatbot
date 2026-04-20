from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from fastapi.responses import JSONResponse
from langchain_core.messages import HumanMessage
from core.llm_factory import get_codegen_llm

router = APIRouter()

class TranslateRequest(BaseModel):
    text: str
    direction: str = "en-to-ar"
    
@router.post("/translate")
async def translate_text(payload: TranslateRequest,request:Request):
    """
    Translate text between English and Arabic.
    Request JSON:
      { "text": "<text>", "direction": "en-to-ar" }
    Allowed directions: en-to-ar, english-to-arabic, ar-to-en, arabic-to-english
    """
    text = payload.text
    direction = payload.direction or "en-to-ar"

    if not text or not text.strip():
        raise HTTPException(status_code=400, detail={'success': False, 'error': 'No text provided'})

    allowed = {'en-to-ar', 'ar-to-en', 'arabic-to-english', 'english-to-arabic'}
    if direction not in allowed:
        raise HTTPException(status_code=400, detail={'success': False, 'error': 'Invalid direction'})

    # Strict prompts
    if direction in ['en-to-ar', 'english-to-arabic']:
        prompt = """Translate the following English text to Arabic. 
Rules:
- Provide ONLY the Arabic translation
- Do not add explanations, notes, or alternative translations
- If technical terms are unclear, keep them in English
- Do not use markdown or formatting
- Keep all abbreviations (like MRO, KPI, CEO, etc.) in English as-is,do not provide the full form.
- Use natural, concise language

Text to translate:
{text}
"""
    else:
        prompt = """Translate the following Arabic text to English.
Rules:
- Provide ONLY the English translation
- Do not add explanations, notes, or alternative translations
- Choose the most common/likely meaning
- Do not use markdown or formatting
- For each abbreviation (like MRO, KPI, CEO, etc.), do not provide the full form. 
- Do not ask for context or clarification

Text to translate:
{text}"""
        

    try:
        llm      = get_codegen_llm()
        response = llm.invoke([HumanMessage(content=prompt.format(text=text))])
        translation = response.text.strip()

        return JSONResponse(
            status_code=200,
            content={
                'success': True,
                'original': text,
                'translation': translation,
                'direction': direction
            }
        )

    except Exception as e:
        # return helpful error structure
        print(f"Translate error: {e}")
        raise HTTPException(status_code=500, detail={'success': False, 'error': str(e)})
