from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
import os

def create_pdf_from_text(text, output_file="output.pdf"):
    """
    Creates a PDF file from input text
    
    Args:
        text (str): Text content to put in the PDF
        output_file (str): Output PDF filename (default: output.pdf)
    """
    # Create PDF document
    doc = SimpleDocTemplate(
        output_file,
        pagesize=letter,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=72
    )
    
    # Prepare styles
    styles = getSampleStyleSheet()
    story = []
    
    # Add title
    title = Paragraph("Generated Document", styles["Title"])
    story.append(title)
    story.append(Spacer(1, 0.25 * inch))
    
    # Process input text
    for paragraph in text.split('\n\n'):
        if paragraph.strip():
            p = Paragraph(paragraph.strip(), styles["BodyText"])
            story.append(p)
            story.append(Spacer(1, 0.1 * inch))
    
    # Build PDF
    doc.build(story)
    return os.path.abspath(output_file)

if __name__ == "__main__":
    print("PDF Creator - Enter your text below")
    print("Type 'DONE' on a new line when finished")
    print("--------------------------------------")
    
    input_lines = []
    while True:
        line = input()
        if line.strip().upper() == "DONE":
            break
        input_lines.append(line)
    
    input_text = "\n".join(input_lines)
    
    if not input_text.strip():
        print("No text provided. Exiting.")
    else:
        # Create PDF
        output_pdf = "custom_document.pdf"
        pdf_path = create_pdf_from_text(input_text, output_pdf)
        print(f"\nPDF created successfully: {pdf_path}")
        print("You can now open this file with any PDF viewer")