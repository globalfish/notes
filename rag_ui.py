from kivy.uix.boxlayout import BoxLayout
from kivy.properties import NumericProperty
from kivy.metrics import sp, dp
from threading import Thread
from kivy.clock import Clock

from rag_pipeline import get_chain
from indexer import run_incremental_indexing

class RagAppUI(BoxLayout):
    # Exposed to kv
    attendee_font_size = NumericProperty(sp(20))
    input_font_size = NumericProperty(sp(20))
    query_font_size = NumericProperty(sp(20))
    response_font_size = NumericProperty(sp(20))
    button_font_size = NumericProperty(sp(24))

    input_height = NumericProperty(dp(46))
    query_height = NumericProperty(dp(100))
    button_height = NumericProperty(dp(48))

    def ask_question(self):
        question = self.ids.query_input.text.strip()
        if not question:
            self.ids.response_label.text = "[color=ff3333]Please enter a question.[/color]"
            return
        self.ids.response_label.text = "[i]Thinking...[/i]"
        Thread(target=self.run_query, args=(question,)).start()

    def run_query(self, question):
        filters = self.build_metadata_filter()
        chain = get_chain(filters)
        try:
            result = chain.invoke(question)
            print (f"Question: \n {question}")
            print (f"Answer: >>>>>> {result.content}")
            # Update UI on main thread
            Clock.schedule_once(lambda dt: self._set_response_text(result.content), 0)
        except Exception as e:
            import traceback
            traceback.print_exc()
            Clock.schedule_once(lambda dt: self._set_response_text(f"[b]Error:[/b] {str(e)}"), 0)

    def index_update(self):
        self.ids.response_label.text = "Scanning for updates..."
        Thread(target=self.run_indexing).start()

    def run_indexing(self):
        try:
            files, chunks = run_incremental_indexing()
            msg = f"Indexed {files} docs → {chunks} chunks." if files else "No new or modified files."
            Clock.schedule_once(lambda dt: self._set_response_text(msg), 0)
        except Exception as e:
            import traceback
            traceback.print_exc()
            Clock.schedule_once(lambda dt: self._set_response_text(f"[b]Indexing error:[/b] {str(e)}"), 0)

    def _set_response_text(self, text):
        """Helper to safely update response label on the main thread."""
        try:
            # If text is an error markup (starts with [b]) set directly
            if isinstance(text, str) and text.startswith("[b]"):
                self.ids.response_label.text = text
            else:
                self.ids.response_label.text = self.format_llm_response(text)
        except Exception:
            # Fallback: set raw text
            try:
                self.ids.response_label.text = str(text)
            except Exception:
                pass

    def clear_filters(self):
        self.ids.attendee_input.text = ""
        self.ids.date_input.text = ""
        self.ids.topic_input.text = ""
        self.ids.filter_summary.text = "Filters: (none)"

    def build_metadata_filter(self):
        filters = []
        summary = []

        a = self.ids.attendee_input.text.strip()
        d = self.ids.date_input.text.strip()
        t = self.ids.topic_input.text.strip()

        if a:
            filters.append({"attendees": {"$ilike": f"%{a}%"}})
            summary.append(f"[i]attendee[/i]=‘{a}’")
        if d:
            filters.append({"date": {"$eq": d}})
            summary.append(f"[i]date[/i]=‘{d}’")
        if t:
            filters.append({"title": {"$ilike": f"%{t}%"}})
            summary.append(f"[i]topic[/i]=‘{t}’")

        self.ids.filter_summary.text = "Filters: " + (", ".join(summary) if summary else "(none)")
        print(filters)
        if not filters:
            return None
        return {"$and": filters}

    @staticmethod
    def format_llm_response(text):
        import re
        text = re.sub(r"\*\*(.*?)\*\*", r"[b]\1[/b]", text)
        text = re.sub(r"\*(.*?)\*", r"[i]\1[/i]", text)
        text = re.sub(r"^- (.*)", r"• \1", text, flags=re.MULTILINE)
        return text.strip()

