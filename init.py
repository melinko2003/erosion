from erosion.pdf import eroPDF

context = {
    "customer_name": "John Doe",
    "invoice_date": "2025-04-24",
    "amount_due": "$1,200.00"
}

pdf = eroPDF("templates/mp_test.json.jinja")
pdf.render(context).save("output/invoice_filled.pdf")
