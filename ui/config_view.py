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
            self, text="Configuração",
            font=ctk.CTkFont(size=20, weight="bold"),
        ).grid(row=0, column=0, pady=(20, 20))

        # Main container
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.grid(row=1, column=0, padx=40)
        main.grid_columnconfigure(0, weight=1)

        left = ctk.CTkFrame(main)
        left.grid(row=0, column=0, sticky="n")

        # Nome
        ctk.CTkLabel(left, text="Dados Pessoais",
                     font=ctk.CTkFont(size=14, weight="bold")).grid(
            row=0, column=0, columnspan=2, padx=20, pady=(15, 10),
        )

        ctk.CTkLabel(left, text="Nome", width=150, anchor="w").grid(
            row=1, column=0, padx=(20, 10), pady=8,
        )
        self.nome_entry = ctk.CTkEntry(left, width=180)
        self.nome_entry.grid(row=1, column=1, padx=(0, 20), pady=8)

        # Financial fields
        ctk.CTkLabel(left, text="Valores Financeiros",
                     font=ctk.CTkFont(size=14, weight="bold")).grid(
            row=2, column=0, columnspan=2, padx=20, pady=(20, 10),
        )

        fields = [
            ("Valor/Hora (R$)", "valor_hora"),
            ("Valor/AE (R$)", "valor_ae"),
            ("VT/Dia (R$)", "vt_dia"),
            ("VR/Dia (R$)", "vr_dia"),
        ]

        self.entries: dict[str, ctk.CTkEntry] = {}
        for i, (label_text, key) in enumerate(fields):
            ctk.CTkLabel(left, text=label_text, width=150, anchor="w").grid(
                row=i + 3, column=0, padx=(20, 10), pady=8,
            )
            entry = ctk.CTkEntry(left, width=120)
            entry.grid(row=i + 3, column=1, padx=(0, 20), pady=8)
            self.entries[key] = entry

        # Save button
        ctk.CTkButton(
            left, text="Salvar", width=150, command=self._save,
        ).grid(row=7, column=0, columnspan=2, pady=15)

        self.status_label = ctk.CTkLabel(left, text="")
        self.status_label.grid(row=8, column=0, columnspan=2)

        self._load()

    def _load(self):
        config = database.get_config()
        self.nome_entry.delete(0, "end")
        self.nome_entry.insert(0, config.nome)
        for key, entry in self.entries.items():
            entry.delete(0, "end")
            val = getattr(config, key)
            entry.insert(0, f"{val:.2f}".replace(".", ","))

    def _save(self):
        try:
            nome = self.nome_entry.get().strip()
            values = {}
            for key, entry in self.entries.items():
                text = entry.get().strip().replace(",", ".")
                values[key] = float(text)

            config = Config(nome=nome, **values)
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
