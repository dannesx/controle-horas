import customtkinter as ctk

import database
from models import Config


class ConfigView(ctk.CTkFrame):
    def __init__(self, parent, on_save_callback=None):
        super().__init__(parent, fg_color="transparent")
        self.on_save_callback = on_save_callback

        self.grid_columnconfigure(0, weight=1)

        # Title
        ctk.CTkLabel(
            self, text="Configuração Financeira",
            font=ctk.CTkFont(size=20, weight="bold"),
        ).grid(row=0, column=0, pady=(20, 30))

        # Form
        form = ctk.CTkFrame(self)
        form.grid(row=1, column=0, padx=40)

        fields = [
            ("Valor/Hora (R$)", "valor_hora"),
            ("Valor/AE (R$)", "valor_ae"),
            ("VT/Dia (R$)", "vt_dia"),
            ("VR/Dia (R$)", "vr_dia"),
        ]

        self.entries: dict[str, ctk.CTkEntry] = {}
        for i, (label_text, key) in enumerate(fields):
            ctk.CTkLabel(form, text=label_text, width=150, anchor="w").grid(
                row=i, column=0, padx=(20, 10), pady=10,
            )
            entry = ctk.CTkEntry(form, width=120)
            entry.grid(row=i, column=1, padx=(0, 20), pady=10)
            self.entries[key] = entry

        # Save button
        ctk.CTkButton(
            self, text="Salvar", width=150, command=self._save,
        ).grid(row=2, column=0, pady=20)

        # Status label
        self.status_label = ctk.CTkLabel(self, text="")
        self.status_label.grid(row=3, column=0)

        # Event types display
        ctk.CTkLabel(
            self, text="Tipos de Evento",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).grid(row=4, column=0, pady=(30, 10))

        et_frame = ctk.CTkFrame(self)
        et_frame.grid(row=5, column=0, padx=40)

        event_types = database.get_event_types()
        for i, et in enumerate(event_types):
            ctk.CTkLabel(
                et_frame, text=f"  {et.name}  ",
                fg_color=et.color, corner_radius=4,
                text_color="white", width=120,
            ).grid(row=i, column=0, padx=20, pady=5)

        self._load()

    def _load(self):
        config = database.get_config()
        for key, entry in self.entries.items():
            entry.delete(0, "end")
            val = getattr(config, key)
            entry.insert(0, f"{val:.2f}".replace(".", ","))

    def _save(self):
        try:
            values = {}
            for key, entry in self.entries.items():
                text = entry.get().strip().replace(",", ".")
                values[key] = float(text)

            config = Config(**values)
            database.update_config(config)
            self.status_label.configure(text="Salvo!", text_color="green")
            self.after(2000, lambda: self.status_label.configure(text=""))

            if self.on_save_callback:
                self.on_save_callback()
        except ValueError:
            self.status_label.configure(
                text="Valor inválido! Use números.", text_color="red",
            )

    def on_show(self):
        self._load()
