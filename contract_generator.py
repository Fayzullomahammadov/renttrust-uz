import os
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
import datetime

def generate_rental_contract_pdf(output_path, contract_data):
    """
    RentTrust UZ — Rasmiy Ijara Shartnomasi va Ko'chib Kirish Dalolatnomasini PDF shaklida yaratish.
    """
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()

    # Maxsus stillar
    header_title_style = ParagraphStyle(
        'HeaderTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=15,
        leading=18,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#065f46')
    )
    
    sub_title_style = ParagraphStyle(
        'SubTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=14,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#1f2937')
    )

    badge_style = ParagraphStyle(
        'Badge',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=10,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#047857')
    )

    body_style = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=12,
        alignment=TA_JUSTIFY,
        textColor=colors.HexColor('#374151')
    )

    section_heading = ParagraphStyle(
        'SectionHeading',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9.5,
        leading=13,
        textColor=colors.HexColor('#065f46')
    )

    small_bold = ParagraphStyle(
        'SmallBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=11,
        textColor=colors.HexColor('#111827')
    )

    small_val = ParagraphStyle(
        'SmallVal',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=11,
        textColor=colors.HexColor('#4b5563')
    )

    story = []

    # 1. Header Banner
    contract_id = contract_data.get('contract_id', 'RT-2026-001')
    contract_date = contract_data.get('date', datetime.date.today().strftime('%d.%m.%Y'))
    
    story.append(Paragraph("RENTTRUST UZ — XAVFSIZ IJARA VA ESCROW PLATFORMASI", badge_style))
    story.append(Spacer(1, 4))
    story.append(Paragraph("TURAR JOYNI IJARAGA BERISH SHARTNOMASI VA DALOLATNOMA", header_title_style))
    story.append(Spacer(1, 3))
    story.append(Paragraph(f"Shartnoma raqami: <b>{contract_id}</b> | Sana: <b>{contract_date} yil</b> | Toshkent shahri", sub_title_style))
    story.append(Spacer(1, 8))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#059669'), spaceBefore=2, spaceAfter=8))

    # 2. Tomonlar ma'lumotlari jadvali
    landlord_name = contract_data.get('landlord_name', 'Mulk Egasi')
    landlord_phone = contract_data.get('landlord_phone', '+998 90 000 00 00')
    tenant_name = contract_data.get('tenant_name', 'Ijarachi')
    tenant_phone = contract_data.get('tenant_phone', '+998 90 000 00 00')
    
    parties_data = [
        [
            Paragraph("<b>IJARAGA BERUVCHI (UY EGASI):</b>", section_heading),
            Paragraph("<b>IJARACHI:</b>", section_heading)
        ],
        [
            Paragraph(f"F.I.SH.: <b>{landlord_name}</b><br/>Aloqa: <b>{landlord_phone}</b><br/>Holati: Tasdiqlangan mulk egasi", small_val),
            Paragraph(f"F.I.SH.: <b>{tenant_name}</b><br/>Aloqa: <b>{tenant_phone}</b><br/>Identifikatsiya: RentTrust UZ orqali tasdiqlangan", small_val)
        ]
    ]
    parties_table = Table(parties_data, colWidths=[260, 260])
    parties_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f9fafb')),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#e5e7eb')),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('PADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(parties_table)
    story.append(Spacer(1, 8))

    # 3. 1-modda: Shartnoma predmeti
    prop_title = contract_data.get('property_title', 'Xonadon')
    district = contract_data.get('district', 'Toshkent')
    address = contract_data.get('address', '')
    rooms = contract_data.get('rooms', 1)
    area = contract_data.get('area_sqm', 45)

    story.append(Paragraph("1. SHARTNOMA PREDMETI", section_heading))
    p1 = (
        f"1.1. Ijaraga beruvchi o'ziga qonuniy tegishli bo'lgan Toshkent shahri, <b>{district} tumani, {address}</b> "
        f"manzilidagi <b>{rooms} xonali (umumiy maydoni {area} m2)</b> bo'lgan turar joyni Ijarachiga vaqtincha yashash uchun ijaraga beradi.<br/>"
        "1.2. Mazkur bitim O'zbekiston Respublikasi Fuqarolik kodeksining 788-moddasi (Kafolatli to'lov) va 831-moddasiga (Agentlik) asosan rasmiylashtirilgan."
    )
    story.append(Paragraph(p1, body_style))
    story.append(Spacer(1, 6))

    # 4. 2-modda: Moliyaviy shartlar va Split komissiya
    rent_uzs = contract_data.get('monthly_rent_uzs', 4000000)
    deposit_uzs = contract_data.get('deposit_uzs', 1000000)
    hold_fee = contract_data.get('hold_fee', 300000)
    split_fee = rent_uzs * 0.02

    story.append(Paragraph("2. IJARA HAQI, DEPOZIT VA 2% SPLIT KOMISSIYA HISOB-KITOBI", section_heading))
    
    finance_table_data = [
        [Paragraph("Ko'rsatkich", small_bold), Paragraph("Miqdori (UZS)", small_bold), Paragraph("Tavsif / Xavfsizlik kafolati", small_bold)],
        [Paragraph("Oylik ijara to'lovi", small_val), Paragraph(f"<b>{rent_uzs:,.0f} so'm</b>", small_val), Paragraph("Har oy kelishilgan sanada to'lanadi", small_val)],
        [Paragraph("Xavfsiz depozit (Escrow)", small_val), Paragraph(f"<b>{deposit_uzs:,.0f} so'm</b>", small_val), Paragraph("RentTrust Escrow hisobida muzlatiladi", small_val)],
        [Paragraph("Platforma xizmat haqi (2%)", small_val), Paragraph(f"<b>{split_fee:,.0f} so'm</b>", small_val), Paragraph("Rieltorlarning 50% komissiyasiga tejamkor muqobil", small_val)],
        [Paragraph("Band qilish depoziti (Hold)", small_val), Paragraph(f"<b>{hold_fee:,.0f} so'm</b>", small_val), Paragraph("24 soatlik kafolatli bandlik uchun qabul qilingan", small_val)]
    ]
    fin_table = Table(finance_table_data, colWidths=[150, 120, 250])
    fin_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#ecfdf5')),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#d1fae5')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e5e7eb')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('PADDING', (0,0), (-1,-1), 4.5),
    ]))
    story.append(fin_table)
    story.append(Spacer(1, 6))

    # 5. 3-modda: Qonuniy imtiyoz (Soliq)
    story.append(Paragraph("3. IJARA.SOLIQ.UZ RO'YXATGA OLISH VA 12% DAROMAD SOLIG'I IMTIYOZI", section_heading))
    p3 = (
        "3.1. Mazkur shartnoma 3 (uch) ish kuni ichida O'zbekiston Respublikasi Davlat Soliq Qo'mitasining <b>ijara.soliq.uz</b> portalida hisobga qo'yiladi.<br/>"
        "3.2. Ijarachi talaba bo'lgan taqdirda, O'zbekiston Respublikasi Soliq kodeksiga binoan Ijaraga beruvchi mazkur ijara daromadidan "
        "<b>12% miqdoridagi Jismoniy shaxslar daromad solig'idan (JShDS) to'liq ozod etiladi</b>."
    )
    story.append(Paragraph(p3, body_style))
    story.append(Spacer(1, 6))

    # 6. 4-modda: Ko'chib kirish dalolatnomasi (Inspection Act)
    notes = contract_data.get('tenant_notes', "Xonadon ko'zdan kechirildi, jihozlar va texnikalar soz holatda qabul qilindi.")
    photos_count = contract_data.get('photos_count', 0)
    
    story.append(Paragraph("4. KO'CHIB KIRISH VA MULKNI QABUL QILISH DALOLATNOMASI", section_heading))
    p4 = (
        f"4.1. Ijarachi xonadonga ko'chib kirish kuni barcha jihozlarni ko'zdan kechirdi. Qayd etilgan holat va nuqsonlar: <i>«{notes}»</i>.<br/>"
        f"4.2. Xonadonning kirish vaqtidagi holatini tasdiqlovchi <b>{photos_count} ta fotosurat</b> RentTrust UZ tizimiga yuklangan bo'lib, "
        "shartnoma muddati tugab depozitni to'liq qaytarishda rasmiy ashyoviy dalil hisoblanadi."
    )
    story.append(Paragraph(p4, body_style))
    story.append(Spacer(1, 8))

    # 7. Imzolar va Escrow Muhr bloki
    sign_data = [
        [
            Paragraph("<b>IJARAGA BERUVCHI:</b><br/>" + landlord_name + "<br/><br/><i>[Raqamli tasdiqlangan: SMS / TG]</i><br/>Sana: " + contract_date, small_val),
            Paragraph("<b>RENTTRUST UZ ESCROW:</b><br/>«RentTrust UZ» MChJ Kafil Agenti<br/><br/><b>[MUHR: ESCROW KAFOLATLANGAN]</b><br/>Litsenziya: №RT-788-UZ", ParagraphStyle('Center', parent=small_val, alignment=TA_CENTER, textColor=colors.HexColor('#065f46'))),
            Paragraph("<b>IJARACHI:</b><br/>" + tenant_name + "<br/><br/><i>[Raqamli tasdiqlangan: WebApp ID]</i><br/>Sana: " + contract_date, ParagraphStyle('Right', parent=small_val, alignment=TA_RIGHT))
        ]
    ]
    sign_table = Table(sign_data, colWidths=[175, 170, 175])
    sign_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f0fdf4')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#059669')),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('PADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(sign_table)

    doc.build(story)
    return output_path

if __name__ == "__main__":
    test_pdf = os.path.join(os.path.dirname(__file__), "test_shartnoma.pdf")
    generate_rental_contract_pdf(test_pdf, {
        "contract_id": "RT-2026-N78",
        "date": "18.10.2026",
        "landlord_name": "Sardor Rahimov",
        "landlord_phone": "+998 90 123 45 67",
        "tenant_name": "Ali Valiyev",
        "tenant_phone": "+998 90 999 88 77",
        "property_title": "Novza metrosi yaqinida 2 xonali kvartira",
        "district": "Chilonzor",
        "address": "Chilonzor 5-mavze, Novza metro ro'parasi",
        "rooms": 2,
        "area_sqm": 56.0,
        "monthly_rent_uzs": 4800000,
        "deposit_uzs": 1500000,
        "hold_fee": 300000,
        "tenant_notes": "Zaldagi stol oyog'ida kichik tirnalish bor, qolgan jihozlar soz holatda.",
        "photos_count": 2
    })
    print("Test PDF muvaffaqiyatli yaratildi:", test_pdf)
