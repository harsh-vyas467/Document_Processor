from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import Paragraph
from reportlab.lib.styles import getSampleStyleSheet
import os

def create_japanese_test_pdf(filename="test_japanese.pdf"):
    # Register Japanese font
    pdfmetrics.registerFont(UnicodeCIDFont("HeiseiMin-W3"))
    
    c = canvas.Canvas(filename, pagesize=A4)
    width, height = A4
    
    # Set font for Japanese characters
    c.setFont("HeiseiMin-W3", 12)
    
    # Title
    c.drawCentredString(width/2, height-50, "テスト文書")
    
    # Company information
    c.drawString(50, height-100, "会社情報:")
    c.drawString(70, height-130, "会社名: 株式会社サンプル")
    c.drawString(70, height-160, "住所: 東京都渋谷区道玄坂1-2-3")
    c.drawString(70, height-190, "電話: 03-1234-5678")
    
    # Invoice details
    c.drawString(50, height-230, "請求書番号: INV-2024-JP-001")
    c.drawString(50, height-260, "発行日: 2024年3月15日")
    c.drawString(50, height-290, "支払期日: 2024年4月15日")
    
    # Product details
    c.drawString(50, height-330, "商品明細:")
    c.drawString(70, height-360, "商品1: ノートパソコン - 数量: 2台 - 単価: 150,000円 - 金額: 300,000円")
    c.drawString(70, height-390, "商品2: モニター - 数量: 3台 - 単価: 50,000円 - 金額: 150,000円")
    c.drawString(70, height-420, "合計金額: 450,000円")
    
    # Notes
    styles = getSampleStyleSheet()
    jstyle = styles["Normal"]
    jstyle.fontName = "HeiseiMin-W3"
    jstyle.fontSize = 12
    note_text = "備考: この請求書はテスト用です。実際の支払いは必要ありません。重要な点は以下の通りです：" \
                "<br/><br/>1. これはシステムテスト用のサンプル文書です<br/>" \
                "2. 実際の支払いは不要です<br/>" \
                "3. ご質問があればサポートまでご連絡ください"
    p = Paragraph(note_text, jstyle)
    p.wrapOn(c, width-100, 100)
    p.drawOn(c, 50, height-520)
    
    c.save()
    print(f"Created test PDF: {filename}")
    return filename

if __name__ == "__main__":
    pdf_file = create_japanese_test_pdf()
    print(f"Japanese test PDF generated: {os.path.abspath(pdf_file)}")