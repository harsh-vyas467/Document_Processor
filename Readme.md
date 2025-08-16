
pip install -r requirements.txt

--
or we can manually install each of them :

pip install flask google-generativeai PyMuPDF pdfplumber reportlab PyPDF2 python-dotenv requests

--

setx GEMINI_API_KEY "<Enter Google api key here>"
--

Available Gemini Models :

run list_gemini_models.py file to get info of all the available models of gemini
---

did this because i have added .env file in previous commit , although it does not contain api key

git rm --cached .env 
add added it to gitegnore


-----