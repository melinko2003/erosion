import json
from pathlib import Path
from typing import Dict

from jinja2 import Environment, FileSystemLoader
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import LETTER
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.acroform import AcroForm


class eroPDF:
    def __init__(self, template_path: str, page_size=LETTER):
        self.template_path = Path(template_path)
        self.page_size = page_size
        self.env = Environment(loader=FileSystemLoader(self.template_path.parent))
        self.template_name = self.template_path.name
        self.rendered_template = None
        self.canvas = None
        self.form = None
        self.layout = {}
        self.rows_per_page = None
        self.page_number = 0

    def render(self, context: Dict) -> "eroPDF":
        template = self.env.get_template(self.template_name)
        rendered_json = template.render(context)
        self.rendered_template = json.loads(rendered_json)
        self.layout = self.rendered_template.get("layout", {})

        page_height = self.page_size[1]
        margin_y = self.layout.get("margin_y", 50)
        row_height = self.layout.get("row_height", 30)
        usable_height = page_height - 2 * margin_y
        self.rows_per_page = usable_height // row_height

        return self

    def save(self, output_path: str):
        self.canvas = canvas.Canvas(output_path, pagesize=self.page_size)
        self.form = self.canvas.acroForm
        self.page_number = 0

        for field in self.rendered_template.get("fields", []):
            row = field.get("row", 0)
            if self._needs_page_break(row):
                self.canvas.showPage()
                self.page_number += 1
                self.form = self.canvas.acroForm
                self._draw_debug_page_number()

            self._draw_field(field)

        self.canvas.showPage()
        self.canvas.save()

    def _needs_page_break(self, row: int) -> bool:
        return row >= (self.page_number + 1) * self.rows_per_page

    def _resolve_coords(self, field: dict) -> tuple:
        if "x" in field and "y" in field:
            return field["x"], field["y"], field.get("width", 100)

        col = field.get("col", 0)
        row = field.get("row", 0)
        col_span = field.get("col_span", 1)

        margin_x = self.layout.get("margin_x", 50)
        margin_y = self.layout.get("margin_y", 50)
        row_height = self.layout.get("row_height", 30)
        col_width = self.layout.get("column_width", 120)

        local_row = row % self.rows_per_page
        x = margin_x + col * col_width
        y = self.page_size[1] - margin_y - local_row * row_height
        width = col_span * col_width
        return x, y, width

    def _draw_debug_page_number(self):
        self.canvas.setFont("Helvetica", 8)
        self.canvas.drawRightString(self.page_size[0] - 40, 20, f"Page {self.page_number + 1}")

    def _draw_field(self, field: Dict):
        field_type = field.get("type")

        if field_type == "text":
            self._draw_text(field)
        elif field_type == "fillable":
            self._draw_fillable(field)
        elif field_type == "checkbox":
            self._draw_checkbox(field)
        elif field_type == "radio":
            self._draw_radio(field)
        elif field_type == "line":
            self._draw_line(field)
        else:
            raise NotImplementedError(f"Unsupported field type: '{field_type}'")

    def _draw_text(self, field: Dict):
        x, y, _ = self._resolve_coords(field)
        font_size = field.get("font_size", 10)
        text = field.get("text", "")

        self.canvas.setFont("Helvetica", font_size)
        self.canvas.drawString(x, y, text)

    def _draw_fillable(self, field: Dict):
        x, y, width = self._resolve_coords(field)
        height = field.get("height", 20)
        self.form.textfield(
            name=field["name"],
            tooltip=field.get("label", ""),
            x=x,
            y=y,
            width=width,
            height=height,
            value=field.get("value", ""),
            borderStyle='underlined',
            forceBorder=True
        )

    def _draw_checkbox(self, field: Dict):
        x, y, _ = self._resolve_coords(field)
        size = field.get("size", 12)
        self.form.checkbox(
            name=field["name"],
            tooltip=field.get("label", ""),
            x=x,
            y=y,
            size=size,
            checked=field.get("checked", False),
            buttonStyle='check'
        )

    def _draw_radio(self, field: Dict):
        for option in field.get("options", []):
            x, y, _ = self._resolve_coords(option)
            size = option.get("size", 12)
            self.form.radio(
                name=field["name"],
                tooltip=field.get("label", ""),
                value=option["value"],
                selected=option.get("selected", False),
                x=x,
                y=y,
                size=size,
                buttonStyle='circle'
            )

    def _draw_line(self, field: Dict):
        x1, y1, _ = self._resolve_coords({"col": field["col1"], "row": field["row1"]})
        x2, y2, _ = self._resolve_coords({"col": field["col2"], "row": field["row2"]})
        self.canvas.setLineWidth(field.get("width", 1))
        self.canvas.line(x1, y1, x2, y2)
