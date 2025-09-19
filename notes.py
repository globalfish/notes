from datetime import datetime, timedelta
from dateutil import parser

import os
import json
from jsonschema import validate, ValidationError
def load_settings(filepath="settings.json"):
    try:
        with open(filepath, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Failed to load settings: {e}")
        return {}
settings = load_settings()

from kivy.utils import platform as kivy_platform
from kivy.config import Config
from kivy.metrics import dp
from kivy.core.window import Window
print(f"Detected platform: {kivy_platform}")
Window.softinput_mode = "below_target"
def get_note_font_size():
    return dp(10)

def get_note_button_height():
    return dp(30)

if kivy_platform == 'linux':
    Config.set('graphics', 'resizable', True)
    Config.set('graphics', 'borderless', False)
    Config.set('graphics', 'width', str(settings.get("window_width", 400)))
    Config.set('graphics', 'height', str(settings.get("window_height", 800)))
folder = settings.get("meeting_notes_dir", "meeting_notes")

from kivy.app import App
from kivy.properties import StringProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.factory import Factory

class MeetingForm(BoxLayout):
    #theme_mode = StringProperty("light")
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        self.all_notes = []
        self.note_popup = None
        self.fields = {}
        self.input_order = []
        self.current_data = None

        #self.build_form()
        #self.link_input_navigation()  # Must come after all inputs are built

    def on_kv_post(self, base_widget):
        self.schema = self.load_schema()
        self.build_form()
        #print(f"🧩 Active tab: {self.__class__.__name__}")
        #print(f"🧾 Schema keys: {list(self.load_schema()['properties'].keys())}")
        self.link_input_navigation()
        #print("KV loaded and bound")

    def load_schema(self):
        with open("note.json", "r") as f:
            return json.load(f)

    def build_form(self):
        for field_name, props in self.schema["properties"].items():
            if not hasattr(self.ids, field_name):
                print(f"⚠️ Skipping unknown field: {field_name}")
                continue
            
            widget = self.ids[field_name]
            hint = props.get("hint", "")
            widget.hint_text = hint

            if field_name == "date" and not widget.text:
                widget.text = datetime.today().strftime("%Y-%m-%d")

            self.fields[field_name] = widget
            self.input_order.append(widget)

    def link_input_navigation(self):
        for i in range(len(self.input_order) - 1):
            self.input_order[i].focus_next = self.input_order[i + 1]

    def get_note_data(self):
        note = {}
        for field, widget in self.fields.items():
            raw = widget.text.strip()
            if field == "attendees":
                note[field] = [x.strip() for x in raw.split(",") if x.strip()]
            elif field == "actionItems":
                note[field] = self.parse_action_items(raw)
            elif field == "date":
                try:
                    note[field] = parser.parse(raw).strftime("%Y-%m-%d")
                except Exception:
                    note[field] = raw
            else:
                note[field] = raw
        return note

    def parse_action_items(self, raw):
        items = []
        for line in raw.strip().splitlines():
            if not line.strip():
                continue
            parts = line.split("|")
            task = parts[0].strip()
            due = parts[1].strip() if len(parts) > 1 else (datetime.today() + timedelta(days=1)).strftime("%Y-%m-%d")
            items.append({"task": task, "dueDate": due})
        return items

    def save_note(self, *_):
        try:
            note = self.get_note_data()
            validate(instance=note, schema=self.schema)
            filename = f"meeting_{note['date']}_{note['meetingTitle'].replace(' ', '_')}.md"
            os.makedirs(folder, exist_ok=True)
            md_text = self._compose_markdown (note)
            with open(os.path.join(folder, filename), "w", encoding="utf-8") as f:
                f.write(md_text)
        except (ValidationError, Exception) as e:
            self.popup("Validation Error", str(e))

    def _compose_markdown(self, data):
        lines = [
            f"# {data.get('meetingTitle', 'Meeting')}",
            f"**Date:** {data.get('date', '')}",
            f"**Attendees:** {', '.join(data.get('attendees', []))}",
            "",
            f"## Notes\n{data.get('notes', '')}"
        ]

        action_items = data.get("actionItems", [])
        if action_items:
            lines.append("\n## Action Items")
            for item in action_items:
                task = item.get("task", "").strip()
                due = item.get("dueDate", "").strip()
                line = f"- [ ] {task}"
                if due:
                    line += f" _(Due: {due})_"
                lines.append(line)

        return "\n".join(lines)

    def clear_form(self, *_):
        for field, widget in self.fields.items():
            widget.text = ""
        if "date" in self.fields:
            self.fields["date"].text = datetime.today().strftime("%Y-%m-%d")
        self.current_data = None


    def load_notes(self, *_):
        if not os.path.exists(folder):
            self.popup("Info", "No meeting notes found.")
            return

        self.all_notes = sorted(os.listdir(folder))
        self.note_popup = NotePopup(meeting_form=self)
        self._populate_note_list(self.note_popup.ids.note_list, self.all_notes)
        self.note_popup.open()

    def _populate_note_list(self, container, files):
        container.clear_widgets()
        for filename in files:
            btn = Factory.FancyButton(
                    text=filename,
                    font_size=get_note_font_size(),
                    size_hint_y=None,
                    height=get_note_button_height()
                    )
            btn.bind(on_release=self.load_selected_note)
            container.add_widget(btn)

    def filter_notes(self, query):
        if not self.note_popup:
            return

        note_list = self.note_popup.ids.note_list
        filtered = [f for f in self.all_notes if query.lower() in f.lower()]
        self._populate_note_list(note_list, filtered)

    def load_selected_note(self, btn):
        with open(os.path.join(folder, btn.text), encoding="utf-8") as f:
            content = f.read()

        data = self._parse_markdown(content)
        self.current_data = data

        # Populate fields from parsed markdown
        for field in self.schema["properties"]:
            if field not in self.fields:
                continue
            if field == "attendees":
                self.fields[field].text = ", ".join(data.get(field, []))
            elif field == "actionItems":
                self.fields[field].text = "\n".join(
                    f"{item['task']} | {item['dueDate']}" if item.get("dueDate") else item["task"]
                    for item in data.get(field, [])
                )
            else:
                self.fields[field].text = data.get(field, "")

        if hasattr(self, "note_popup"):
            self.note_popup.dismiss()

    def _parse_markdown(self, text):
        import re
        lines = text.splitlines()
        data = {
            "meetingTitle": "",
            "date": "",
            "attendees": [],
            "notes": "",
            "actionItems": []
        }

        in_notes = False
        notes_lines = []

        def extract_field(patterns):
            for pattern in patterns:
                for line in lines:
                    match = re.search(pattern, line, re.IGNORECASE)
                    if match:
                        return match.group(1).strip()
            return ""

        # Extract metadata
        data["date"] = extract_field([
            r"\*\*Date\*\*\s*:\s*(.+)",
            r"Date\s*:\s*(.+)"
        ])

        attendees_field = extract_field([
            r"\*\*Attendees\*\*\s*:\s*(.+)",
            r"Attendees\s*:\s*(.+)"
        ])
        data["attendees"] = [a.strip() for a in attendees_field.split(",") if a.strip()]

        data["meetingTitle"] = extract_field([
            r"\*\*Title\*\*\s*:\s*(.+)",
            r"#\s*(.+)"
        ])

        # Extract notes and actions
        note_blocks = re.findall(r"#{2,3}\s*(Notes|Topics)\s*\n((?:- .+\n)+)", text, flags=re.IGNORECASE)
        action_blocks = re.findall(r"##\s*Action Items\s*\n((?:-\[.\].+\n)+)", text, re.IGNORECASE)

        if note_blocks:
            data["notes"] = "\n".join(line[2:].strip() for _, block in note_blocks for line in block.strip().splitlines())

        if action_blocks:
            data["actionItems"] = [
                {"task": line[2:].strip(), "dueDate": ""}
                for block in action_blocks
                for line in block.strip().splitlines()
            ]

        return data


    def build_buttons(self):
        row = BoxLayout(size_hint_y=None, height=50, spacing=10)
        row.add_widget(Button(text="Save", on_press=self.save_note))
        row.add_widget(Button(text="Clear", on_press=self.clear_form))
        row.add_widget(Button(text="Load Notes", on_press=self.load_notes))
        self.add_widget(row)

    def popup(self, title, msg):
        popup = Popup(title=title, size_hint=(0.9, 0.9))
        popup.content = TextInput(text=msg, readonly=True, multiline=True)
        popup.open()
from kivy.uix.popup import Popup
class NotePopup(Popup):
    def __init__(self, meeting_form, **kwargs):
        super().__init__(**kwargs)
        self.meeting_form = meeting_form