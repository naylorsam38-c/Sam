# Harvested by harvest_parts.py
# capability : CAP-0015 (generate invoice)
# from       : invoice-generator @ 14f0b74b979604e970dc1b14e803581c42e78b2d
# source     : server.py:265-284
# licence    : MIT (LICENSE)
# NOTE: this file is evidence, not a standalone module -- it depends on names from the source application's own modules (see PROVENANCE.json 'dependencies'). It is not imported directly; build.py binds it into a verified, running instance of the source application.

def generate_invoice_pdf(invoice_id):
    theme = request.args.get('theme', 'default')
    
    valid_themes = ['default', 'modern', 'minimalist', 'classic', 'creative', 'technical']
    if theme not in valid_themes:
        return "Invalid theme selected", 400

    template_name = f"invoice_pdf_{theme}.html" if theme != 'default' else "invoice_pdf.html"
    
    pdf_data = get_pdf_data(invoice_id)
    if not pdf_data:
        return "Invoice not found", 404

    html = render_template(template_name, **pdf_data)
    pdf = HTML(string=html).write_pdf()
    
    filename = f'invoice_{pdf_data["invoice"]["invoice_no"].replace("/", "-")}.pdf'
    return Response(pdf, mimetype='application/pdf', headers={
        'Content-Disposition': f'inline; filename={filename}'
    })
