Built an AI-powered multilingual document processor that extracts structured data, translates content, and summarizes PDFs with customizable user instructions.

Key features:
- Language detection with confidence scoring
- Customizable JSON extraction
- Layout-preserving PDF translation
- Summarization in TXT/PDF formats
- User-customizable processing prompts
- Multi-format output generation
- Secure file handling
- Gemini AI integration

The system automatically detects document language, extracts entities, translates while preserving formatting, and generates summaries - all with optional user-specified processing rules for each output type.


---------------------------------------------------------------------------------------------------------------

pip install -r requirements.txt

--
or we can manually install each of them :

pip install flask google-generativeai PyMuPDF pdfplumber reportlab PyPDF2 python-dotenv requests

--

setx GEMINI_API_KEY "<EnterGoogleApiKeyHere>"
--

Available Gemini Models :

run list_gemini_models.py file to get info of all the available models of gemini
---

did this because i have added .env file in previous commit , although it does not contain api key

git rm --cached .env 
add added it to gitegnore


-----