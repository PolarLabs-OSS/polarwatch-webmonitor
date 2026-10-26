"""PolarWatch 2.1 — PolarLabs premium minimal desktop UI.

Modern CustomTkinter presentation only. No database, user accounts,
payments, mining, wallet, or remote services. The monitoring core owns
all user-selected HTTP/DNS/TLS diagnostics.
"""
from __future__ import annotations

import queue
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from tkinter import Canvas, messagebox

import customtkinter as ctk
from PIL import Image

from polarwatch_monitor_core import (
    load_sites, save_sites, new_site, probe_site,
)

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")
# Force sensible physical geometry on high-DPI Surface displays.
# Otherwise Windows auto scaling can double the whole window.
ctk.set_widget_scaling(1.0)
ctk.set_window_scaling(1.0)

P = {
    "background": "#07141F",
    "sidebar": "#0A1C2A",
    "card": "#102636",
    "card_hover": "#173647",
    "inner": "#0D2130",
    "line": "#214052",
    "text": "#EDF8FB",
    "muted": "#91A9B7",
    "faint": "#647F90",
    "cyan": "#6ADBD9",
    "turquoise": "#40BFC3",
    "green": "#6DE0AD",
    "red": "#FB8B98",
    "yellow": "#EDC77B",
    "green_bg": "#183B36",
    "red_bg": "#422C39",
    "dim_bg": "#1A3341",
}
FONT = "Segoe UI"
MONO = "Consolas"

def text(parent, value, size=12, color="text", bold=False, **kwargs):
    return ctk.CTkLabel(
        parent, text=value, font=ctk.CTkFont(family=FONT, size=size, weight="bold" if bold else "normal"),
        text_color=P.get(color, color), **kwargs,
    )

def button(parent, title, command, kind="subtle", width=0, height=40):
    palette = {
        "primary": (P["turquoise"], "#279AA4", P["background"]),
        "subtle": (P["card_hover"], "#20485B", P["text"]),
        "ghost": ("transparent", P["card_hover"], P["muted"]),
        "danger": (P["red_bg"], "#633546", P["red"]),
    }
    fg, hover, color = palette[kind]
    return ctk.CTkButton(
        parent, text=title, command=command, width=width, height=height,
        corner_radius=10, fg_color=fg, hover_color=hover,
        text_color=color, font=ctk.CTkFont(family=FONT, size=12, weight="bold"),
    )

def card(parent, radius=15, color="card"):
    return ctk.CTkFrame(
        parent, fg_color=P[color], corner_radius=radius,
        border_width=1, border_color=P["line"],
    )

class PolarWatchModern:
    def __init__(self, root, *, sites=None, autostart=True):
        self.root = root
        self.root.title("PolarWatch — Website Monitor | PolarLabs")
        self.root.geometry("1370x830")
        self.root.minsize(1080, 680)
        self.root.configure(fg_color=P["background"])
        self.root.protocol("WM_DELETE_WINDOW", self.close)

        self.closed = False
        self.events = queue.Queue()
        self.error_on_load = None
        if sites is None:
            try:
                self.sites = load_sites()
            except ValueError as exc:
                self.sites = []
                self.error_on_load = str(exc)
        else:
            self.sites = list(sites)
        self.selected = self.sites[0]["id"] if self.sites else None
        self.results = {}
        self.series = {}
        self.working = False
        self.scan_token = 0
        self.interval_seconds = 300
        self.next_scan_at = float("inf")
        self.expert = False
        self.report_label = "Pronto · Nessun database né account"
        self.last_check_text = "Nessun controllo effettuato"
        self._build_shell()
        self.render()
        self._poll_after=self.root.after(250, self.poll)
        if self.error_on_load:
            self.set_notice(self.error_on_load, "red")
        if autostart and self.sites:
            self.root.after(850, self.scan_all)

    def _load_logo(self, parent):
        base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
        relative = Path("assets")
        candidates = [
            base / relative / "polarwatch_neon_icon.png",
            Path(__file__).resolve().parent / relative / "polarwatch_neon_icon.png",
        ]
        for path in candidates:
            if path.is_file():
                try:
                    image = Image.open(path).convert("RGBA")
                    self.logo = ctk.CTkImage(light_image=image, dark_image=image, size=(62, 62))
                    ctk.CTkLabel(parent, image=self.logo, text="").pack(side="left", padx=(0, 11))
                    # Match the taskbar/titlebar icon to the PolarWatch neon artwork.
                    import tkinter as tk
                    self.window_icon = tk.PhotoImage(file=str(path))
                    self.root.iconphoto(True, self.window_icon)
                    ico_path = path.with_suffix(".ico")
                    if ico_path.is_file() and sys.platform == "win32":
                        try:
                            self.root.iconbitmap(str(ico_path))
                        except (tk.TclError, OSError):
                            pass
                    return
                except (OSError, ValueError):
                    pass
        text(parent, "◈", 30, "cyan", True).pack(side="left", padx=(0, 12))

    def _build_shell(self):
        root = self.root
        root.grid_columnconfigure(0, weight=0, minsize=236)
        root.grid_columnconfigure(1, weight=1)
        root.grid_rowconfigure(0, weight=1)

        nav = ctk.CTkFrame(root, width=235, fg_color=P["sidebar"], corner_radius=0)
        nav.grid(row=0, column=0, sticky="nsw")
        nav.grid_propagate(False)
        nav.grid_columnconfigure(0, weight=1)
        nav.grid_rowconfigure(5, weight=1)

        brand = ctk.CTkFrame(nav, fg_color="transparent")
        brand.grid(row=0, column=0, sticky="ew", padx=19, pady=(27, 38))
        self._load_logo(brand)
        identity = ctk.CTkFrame(brand, fg_color="transparent")
        identity.pack(side="left", fill="x")
        text(identity, "POLARWATCH", 16, "text", True).pack(anchor="w")
        text(identity, "WEBSITE MONITOR", 10, "cyan", True).pack(anchor="w", pady=(3, 0))

        actions = ctk.CTkFrame(nav, fg_color="transparent")
        actions.grid(row=1, column=0, sticky="ew", padx=17)
        text(actions, "MONITORAGGIO", 10, "faint", True).pack(anchor="w", pady=(0, 12))
        button(actions, "＋   Aggiungi sito", self.add_dialog, "primary", height=44).pack(fill="x", pady=(0, 11))
        button(actions, "↻   Controlla tutti", self.scan_all, height=42).pack(fill="x", pady=(0, 7))
        button(actions, "◎   Controlla selezionato", self.scan_selected, height=42).pack(fill="x", pady=(0, 7))
        button(actions, "−   Rimuovi sito", self.remove_selected, "ghost", height=40).pack(fill="x")

        ctk.CTkFrame(nav, fg_color=P["line"], height=1).grid(
            row=2, column=0, sticky="ew", padx=19, pady=(25, 23))
        settings = ctk.CTkFrame(nav, fg_color="transparent")
        settings.grid(row=3, column=0, sticky="ew", padx=17)
        text(settings, "CONTROLLO AUTOMATICO", 10, "faint", True).pack(anchor="w", pady=(0, 11))
        self.interval_menu = ctk.CTkOptionMenu(
            settings, values=["Off", "1 min", "5 min", "15 min", "30 min", "60 min"],
            command=self.change_interval, height=40, corner_radius=9,
            fg_color=P["card_hover"], button_color="#20485C",
            button_hover_color="#2A586B", dropdown_fg_color=P["card"],
            dropdown_hover_color=P["card_hover"], text_color=P["text"],
            font=ctk.CTkFont(family=FONT, size=12),
            dropdown_font=ctk.CTkFont(family=FONT, size=12),
        )
        self.interval_menu.set("5 min")
        self.interval_menu.pack(fill="x")
        self.interval_info = text(settings, "●  Attivo · ogni 5 minuti", 10, "green")
        self.interval_info.pack(anchor="w", pady=(11, 0))

        ctk.CTkFrame(nav, fg_color=P["line"], height=1).grid(
            row=4, column=0, sticky="ew", padx=19, pady=(23, 22))
        extra = ctk.CTkFrame(nav, fg_color="transparent")
        extra.grid(row=5, column=0, sticky="new", padx=17)
        text(extra, "STRUMENTI", 10, "faint", True).pack(anchor="w", pady=(0, 12))
        self.expert_switch = ctk.CTkSwitch(
            extra, text="Modalità esperto", command=self.toggle_expert,
            progress_color=P["turquoise"], button_color=P["text"],
            button_hover_color=P["cyan"], fg_color=P["line"],
            text_color=P["text"], font=ctk.CTkFont(family=FONT, size=12),
        )
        self.expert_switch.pack(fill="x", pady=(3, 15))
        button(extra, "▤   Copia report", self.copy_report, "subtle", height=39).pack(fill="x")

        foot = ctk.CTkFrame(nav, fg_color="transparent")
        foot.grid(row=6, column=0, sticky="sew", padx=19, pady=(8, 24))
        text(foot, "●  100% LOCALE", 10, "cyan", True).pack(anchor="w")
        text(foot, "Solo elenco siti in JSON", 10, "muted").pack(anchor="w", pady=(5, 0))
        text(foot, "PolarLabs  /  2.1", 10, "faint").pack(anchor="w", pady=(3, 0))

        content = ctk.CTkFrame(root, fg_color="transparent")
        content.grid(row=0, column=1, sticky="nsew", padx=27, pady=(23, 18))
        content.grid_columnconfigure(0, weight=1)
        content.grid_rowconfigure(2, weight=1)
        self.content = content

        header = ctk.CTkFrame(content, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 22))
        header.grid_columnconfigure(0, weight=1)
        self.heading = text(header, "Panoramica siti", 26, "text", True)
        self.heading.grid(row=0, column=0, sticky="w")
        text(header, "Prestazioni, disponibilità e diagnostica in tempo reale.",
             12, "muted").grid(row=1, column=0, sticky="w", pady=(7, 0))
        badges = ctk.CTkFrame(header, fg_color="transparent")
        badges.grid(row=0, column=1, rowspan=2, sticky="e")
        ctk.CTkLabel(badges, text="  ●  MONITOR LOCALE  ", fg_color=P["green_bg"],
                     corner_radius=12, text_color=P["green"], height=27,
                     font=ctk.CTkFont(family=MONO, size=10, weight="bold")).pack(anchor="e")
        self.checked_var = ctk.StringVar(value=self.last_check_text)
        ctk.CTkLabel(badges, textvariable=self.checked_var, text_color=P["muted"],
                     font=ctk.CTkFont(family=FONT, size=11)).pack(anchor="e", pady=(9, 0))

        summaries = ctk.CTkFrame(content, fg_color="transparent")
        summaries.grid(row=1, column=0, sticky="ew", pady=(0, 19))
        self.summary_vars = {}
        for i,(key,label,color,sign) in enumerate((
            ("all", "SITI MONITORATI", "cyan", "◈"),
            ("up", "ONLINE", "green", "●"),
            ("down", "OFFLINE", "red", "●"),
            ("avg", "RISPOSTA MEDIA", "yellow", "⌁"),
        )):
            summaries.grid_columnconfigure(i, weight=1, uniform="overview")
            frame = card(summaries)
            frame.grid(row=0, column=i, sticky="nsew", padx=(0,10 if i<3 else 0))
            caption = ctk.CTkFrame(frame, fg_color="transparent")
            caption.pack(fill="x", padx=17, pady=(13, 0))
            text(caption, sign, 12, color, True).pack(side="left", padx=(0,8))
            text(caption, label, 10, "muted", True).pack(side="left")
            var=ctk.StringVar(value="—")
            self.summary_vars[key]=var
            ctk.CTkLabel(frame,textvariable=var,text_color=P[color],
                         font=ctk.CTkFont(family=MONO,size=27,weight="bold"),
                         anchor="w").pack(fill="x",padx=17,pady=(8,13))

        workspace = ctk.CTkFrame(content, fg_color="transparent")
        workspace.grid(row=2,column=0,sticky="nsew")
        workspace.grid_columnconfigure(0,weight=6,uniform="workspace")
        workspace.grid_columnconfigure(1,weight=5,uniform="workspace")
        workspace.grid_rowconfigure(0,weight=1)
        left = ctk.CTkFrame(workspace,fg_color="transparent")
        left.grid(row=0,column=0,sticky="nsew",padx=(0,13))
        left.grid_columnconfigure(0,weight=1)
        left.grid_rowconfigure(0,weight=3)
        left.grid_rowconfigure(1,weight=2)
        listed = card(left)
        listed.grid(row=0,column=0,sticky="nsew",pady=(0,13))
        listed.grid_columnconfigure(0,weight=1)
        listed.grid_rowconfigure(1,weight=1)
        list_header=ctk.CTkFrame(listed,fg_color="transparent")
        list_header.grid(row=0,column=0,sticky="ew",padx=17,pady=(14,8))
        text(list_header,"I TUOI SITI",11,"text",True).pack(side="left")
        text(list_header,"Clicca per dettagli",10,"faint").pack(side="right")
        self.list_area=ctk.CTkScrollableFrame(listed,fg_color="transparent",
                                               corner_radius=0,
                                               scrollbar_button_color=P["line"],
                                               scrollbar_button_hover_color=P["card_hover"])
        self.list_area.grid(row=1,column=0,sticky="nsew",padx=(12,7),pady=(0,12))
        self.list_area.grid_columnconfigure(0,weight=1)
        chart=card(left)
        chart.grid(row=1,column=0,sticky="nsew")
        chart.grid_rowconfigure(1,weight=1)
        chart.grid_columnconfigure(0,weight=1)
        text(chart,"LATENZA  /  SESSIONE CORRENTE",10,"muted",True).grid(
            row=0,column=0,sticky="w",padx=17,pady=(13,0))
        self.graph=Canvas(chart,bg=P["card"],bd=0,highlightthickness=0,height=133)
        self.graph.grid(row=1,column=0,sticky="nsew",padx=13,pady=(4,11))
        self.graph.bind("<Configure>",lambda _:self.draw_graph())

        detail=card(workspace)
        detail.grid(row=0,column=1,sticky="nsew")
        detail.grid_rowconfigure(1,weight=1)
        detail.grid_columnconfigure(0,weight=1)
        detail_top=ctk.CTkFrame(detail,fg_color="transparent")
        detail_top.grid(row=0,column=0,sticky="ew",padx=18,pady=(15,11))
        text(detail_top,"DETTAGLIO SITO",11,"text",True).pack(side="left")
        self.mode_chip=ctk.CTkLabel(detail_top,text="ESSENZIALE",
                                     fg_color=P["dim_bg"],corner_radius=10,
                                     text_color=P["muted"],height=25,
                                     font=ctk.CTkFont(family=MONO,size=10))
        self.mode_chip.pack(side="right")
        self.detail_area=ctk.CTkScrollableFrame(
            detail,fg_color="transparent",corner_radius=0,
            scrollbar_button_color=P["line"],
            scrollbar_button_hover_color=P["card_hover"])
        self.detail_area.grid(row=1,column=0,sticky="nsew",padx=(17,9),pady=(0,14))
        self.detail_area.grid_columnconfigure(0,weight=1)

        footer=ctk.CTkFrame(content,fg_color="transparent")
        footer.grid(row=3,column=0,sticky="ew",pady=(15,0))
        footer.grid_columnconfigure(0,weight=1)
        self.notice=ctk.StringVar(value=self.report_label)
        self.notice_widget=ctk.CTkLabel(
            footer,textvariable=self.notice,text_color=P["muted"],
            font=ctk.CTkFont(family=FONT,size=11),anchor="w")
        self.notice_widget.grid(row=0,column=0,sticky="ew")
        text(footer,"NESSUNO STORICO SALVATO",9,"faint",True).grid(row=0,column=1,sticky="e")

    def set_notice(self, message, tone="muted"):
        self.notice.set(message)
        self.notice_widget.configure(text_color=P.get(tone,P["muted"]))

    def _summary(self):
        values = list(self.results.get(s["id"]) for s in self.sites)
        online = [r for r in values if r and r.get("state")=="UP"]
        down = [r for r in values if r and r.get("state")=="DOWN"]
        speeds = [r["latency"] for r in online if isinstance(r.get("latency"),(int,float))]
        for key,value in (
            ("all",str(len(self.sites))),
            ("up",str(len(online))),
            ("down",str(len(down))),
            ("avg",f"{round(sum(speeds)/len(speeds))} ms" if speeds else "—"),
        ):
            self.summary_vars[key].set(value)

    def _status(self, r):
        if not r:
            return "IN ATTESA", "muted", "dim_bg"
        if r.get("state")=="UP":
            return "● ONLINE", "green", "green_bg"
        if r.get("state")=="DOWN":
            return "● OFFLINE", "red", "red_bg"
        return "IN ATTESA", "muted", "dim_bg"

    def _refresh_sites(self):
        for child in self.list_area.winfo_children():
            child.destroy()
        if not self.sites:
            empty=ctk.CTkFrame(self.list_area,fg_color=P["inner"],corner_radius=12)
            empty.grid(row=0,column=0,sticky="ew",padx=4,pady=22)
            text(empty,"◎",30,"cyan").pack(pady=(28,5))
            text(empty,"Nessun sito monitorato",14,"text",True).pack(pady=(0,5))
            text(empty,"Aggiungi il primo sito per iniziare.",11,"muted").pack(pady=(0,27))
            return
        heading=ctk.CTkFrame(self.list_area,fg_color="transparent")
        heading.grid(row=0,column=0,sticky="ew",padx=6,pady=(0,7))
        heading.grid_columnconfigure(0,weight=1)
        text(heading,"SITO",9,"faint",True).grid(row=0,column=0,sticky="w",padx=10)
        text(heading,"RISPOSTA",9,"faint",True).grid(row=0,column=1,sticky="e",padx=11)
        for index,site in enumerate(self.sites,1):
            self._site_row(index,site)

    def _site_row(self, index, site):
        sid=site["id"]
        r=self.results.get(sid)
        status,color,status_bg=self._status(r)
        selected=sid==self.selected
        surface=P["card_hover"] if selected else P["inner"]
        row=ctk.CTkFrame(self.list_area,fg_color=surface,corner_radius=12,
                         border_width=1 if selected else 0,
                         border_color=P["turquoise"] if selected else surface)
        row.grid(row=index,column=0,sticky="ew",padx=3,pady=5)
        row.grid_columnconfigure(0,weight=1)

        info=ctk.CTkFrame(row,fg_color="transparent")
        info.grid(row=0,column=0,sticky="ew",padx=13,pady=11)
        info.grid_columnconfigure(0,weight=1)
        name=ctk.CTkButton(info,text=site["name"],anchor="w",height=25,
                            fg_color="transparent",hover_color=P["card_hover"],
                            text_color=P["text"],font=ctk.CTkFont(family=FONT,size=12,weight="bold"),
                            corner_radius=6,command=lambda sid=sid:self.select_site(sid))
        name.grid(row=0,column=0,sticky="ew")
        host=site["url"].split("://",1)[-1].split("/",1)[0]
        sub=text(info,host[:43],10,"faint")
        sub.grid(row=1,column=0,sticky="w",padx=7,pady=(0,3))
        for w in (sub,info,row):
            w.bind("<Button-1>",lambda _e,sid=sid:self.select_site(sid))
        ctk.CTkLabel(info,text=status,fg_color=P[status_bg],
                     text_color=P[color],corner_radius=9,height=23,
                     font=ctk.CTkFont(family=FONT,size=10,weight="bold")).grid(
                         row=2,column=0,sticky="w",padx=7,pady=(5,0))

        metric=ctk.CTkFrame(row,fg_color="transparent")
        metric.grid(row=0,column=1,sticky="e",padx=(3,14))
        latency=(f'{r["latency"]} ms' if r and isinstance(r.get("latency"),(int,float)) else "—")
        text(metric,latency,14,"text",True).pack(anchor="e")
        ssl_days=r.get("ssl_days") if r else None
        ssl_color="yellow" if ssl_days is not None and ssl_days<15 else "muted"
        text(metric,f"TLS {ssl_days} gg" if ssl_days is not None else "TLS —",
             9,ssl_color).pack(anchor="e",pady=(6,0))
        for w in (metric,):
            w.bind("<Button-1>",lambda _e,sid=sid:self.select_site(sid))

    def select_site(self, sid):
        if sid!=self.selected and any(s["id"]==sid for s in self.sites):
            self.selected=sid
            self._refresh_sites()
            self._render_details()
            self.draw_graph()

    def selected_site(self):
        return next((s for s in self.sites if s["id"]==self.selected),None)

    def _detail_heading(self, parent, label, color="muted"):
        text(parent,label,10,color,True,anchor="w").pack(fill="x",pady=(13,5))

    def _detail_value(self, parent, title, value, tone="text"):
        frame=ctk.CTkFrame(parent,fg_color=P["inner"],corner_radius=10)
        frame.pack(fill="x",pady=4)
        frame.grid_columnconfigure(0,weight=1)
        text(frame,title,10,"muted").grid(row=0,column=0,sticky="w",padx=11,pady=(9,0))
        label=text(frame,str(value),12,tone,True,wraplength=325,justify="left",anchor="w")
        label.grid(row=1,column=0,sticky="ew",padx=11,pady=(3,10))

    def _render_details(self):
        for child in self.detail_area.winfo_children():
            child.destroy()
        site=self.selected_site()
        if not site:
            spacer=ctk.CTkFrame(self.detail_area,fg_color="transparent",height=40)
            spacer.pack()
            text(self.detail_area,"◎",36,"cyan").pack(pady=(8,12))
            text(self.detail_area,"Nessun sito selezionato",15,"text",True).pack()
            text(self.detail_area,"Aggiungi un sito oppure selezionalo dalla lista.",
                 11,"muted",wraplength=285,justify="center").pack(pady=(10,16))
            return
        r=self.results.get(site["id"])
        self.mode_chip.configure(
            text="ESPERTO" if self.expert else "ESSENZIALE",
            text_color=P["cyan"] if self.expert else P["muted"],
            fg_color=P["dim_bg"])
        title=text(self.detail_area,site["name"],19,"text",True,wraplength=345,justify="left")
        title.pack(anchor="w",pady=(1,7))
        state,col,bg=self._status(r)
        chip=ctk.CTkLabel(self.detail_area,text="   "+state+"   ",
                          fg_color=P[bg],text_color=P[col],corner_radius=10,
                          font=ctk.CTkFont(family=FONT,size=11,weight="bold"),
                          height=27)
        chip.pack(anchor="w",pady=(0,13))
        self._detail_value(self.detail_area,"INDIRIZZO",site["url"],"cyan")
        if not r:
            text(self.detail_area,"Nessun controllo ancora eseguito.",12,"muted").pack(
                anchor="w",pady=14)
            return
        self._detail_heading(self.detail_area,"PANORAMICA")
        self._detail_value(self.detail_area,"STATO HTTP",str(r.get("code") or "Non disponibile"),
                           "green" if r.get("state")=="UP" else "red")
        millis=r.get("latency")
        self._detail_value(self.detail_area,"TEMPO DI RISPOSTA",f"{millis} ms" if millis is not None else "—")
        self._detail_value(self.detail_area,"ULTIMO CONTROLLO",r.get("checked") or "—")
        expires=r.get("ssl_days")
        self._detail_value(self.detail_area,"CERTIFICATO TLS",
                           f"{expires} giorni rimanenti" if expires is not None else "Non disponibile",
                           "yellow" if expires is not None and expires<15 else "text")
        if r.get("error"):
            self._detail_value(self.detail_area,"PROBLEMA RILEVATO",r["error"],"red")
        if not self.expert:
            text(self.detail_area,"Attiva Modalità esperto per aprire DNS, TLS,",
                 10,"faint").pack(anchor="w",pady=(12,2))
            text(self.detail_area,"TTFB, redirect e header di sicurezza.",
                 10,"faint").pack(anchor="w")
            return
        self._detail_heading(self.detail_area,"PRESTAZIONI E RETE","cyan")
        ttfb=r.get("ttfb")
        dns_ms=r.get("dns_ms")
        self._detail_value(self.detail_area,"TTFB",f"{ttfb} ms" if ttfb is not None else "—")
        self._detail_value(self.detail_area,"RISOLUZIONE DNS",f"{dns_ms} ms" if dns_ms is not None else "—")
        self._detail_value(self.detail_area,"IP RISOLTI",", ".join(r.get("dns") or []) or "Non disponibili")
        self._detail_value(self.detail_area,"URL FINALE",r.get("final_url") or site["url"])
        self._detail_value(self.detail_area,"REDIRECT","Sì" if r.get("redirect") else "No")
        self._detail_heading(self.detail_area,"TLS E HTTP","cyan")
        self._detail_value(self.detail_area,"VERSIONE TLS",r.get("tls") or "—")
        self._detail_value(self.detail_area,"CIFRATURA",r.get("cipher") or "—")
        self._detail_value(self.detail_area,"SCADENZA TLS",r.get("ssl_until") or "—")
        self._detail_value(self.detail_area,"SERVER",r.get("server") or "—")
        self._detail_value(self.detail_area,"CONTENT-TYPE",r.get("type") or "—")
        self._detail_heading(self.detail_area,"HEADER DI SICUREZZA","cyan")
        for label, present in (r.get("security_headers") or {}).items():
            self._detail_value(self.detail_area,label,"● Presente" if present else "○ Assente",
                               "green" if present else "yellow")
        text(self.detail_area,"La presenza degli header non sostituisce un audit.",
             10,"faint",wraplength=310,justify="left").pack(anchor="w",pady=(8,4))
        for note in r.get("notes") or []:
            self._detail_value(self.detail_area,"NOTA",note,"yellow")

    def draw_graph(self):
        cv=self.graph
        cv.delete("all")
        w=max(cv.winfo_width(),140)
        h=max(cv.winfo_height(),100)
        samples=self.series.get(self.selected,[])
        l,r,t,b=19,w-18,18,h-21
        for frac in (0.25,0.5,0.75):
            y=t+(b-t)*frac
            cv.create_line(l,y,r,y,fill="#1E3D4E",dash=(3,6))
        cv.create_line(l,b,r,b,fill=P["line"])
        if not samples:
            cv.create_text(w/2,h/2,fill=P["faint"],
                           text="I dati appariranno dopo i primi controlli",
                           font=(FONT,11))
            return
        m=max(100,max(samples)*1.2)
        coords=[]
        for i,val in enumerate(samples):
            coords.extend((
                l+i/max(1,len(samples)-1)*(r-l),
                b-(val/m)*(b-t),
            ))
        if len(coords)>=4:
            cv.create_line(*coords,fill=P["cyan"],width=3,
                           capstyle="round",joinstyle="round")
        x,y=coords[-2:]
        cv.create_oval(x-4,y-4,x+4,y+4,outline=P["cyan"],fill=P["green"],width=2)
        cv.create_text(r,t,anchor="ne",text=f"max {max(samples)} ms",
                       fill=P["muted"],font=(MONO,9))
        cv.create_text(r,b+12,anchor="se",text=f"ultimo {samples[-1]} ms",
                       fill=P["green"],font=(MONO,9))

    def render(self):
        self._summary()
        self._refresh_sites()
        self._render_details()
        self.draw_graph()

    def _popup(self,title,width=455,height=345):
        win=ctk.CTkToplevel(self.root)
        win.withdraw()
        win.configure(fg_color=P["sidebar"])
        win.title("PolarWatch · "+title)
        win.geometry(f"{width}x{height}")
        win.resizable(False,False)
        win.transient(self.root)
        self.root.update_idletasks()
        x=max(0,self.root.winfo_rootx()+(self.root.winfo_width()-width)//2)
        y=max(0,self.root.winfo_rooty()+(self.root.winfo_height()-height)//2)
        win.geometry(f"{width}x{height}+{x}+{y}")
        win.deiconify()
        win.lift()
        win.grab_set()
        return win

    def add_dialog(self):
        win=self._popup("Aggiungi sito")
        shell=ctk.CTkFrame(win,fg_color="transparent")
        shell.pack(fill="both",expand=True,padx=25,pady=23)
        text(shell,"Aggiungi un sito",21,"text",True).pack(anchor="w")
        text(shell,"Inizia a monitorare URL, latenza e TLS.",
             11,"muted").pack(anchor="w",pady=(6,19))
        text(shell,"Nome (facoltativo)",11,"muted").pack(anchor="w",pady=(0,5))
        name=ctk.CTkEntry(shell,height=39,placeholder_text="Es. PolarLabs",
                          fg_color=P["card"],border_color=P["line"],corner_radius=9,
                          text_color=P["text"])
        name.pack(fill="x",pady=(0,14))
        text(shell,"Indirizzo del sito",11,"muted").pack(anchor="w",pady=(0,5))
        url=ctk.CTkEntry(shell,height=39,placeholder_text="https://esempio.it",
                         fg_color=P["card"],border_color=P["line"],corner_radius=9,
                         text_color=P["text"])
        url.pack(fill="x",pady=(0,17))
        actions=ctk.CTkFrame(shell,fg_color="transparent")
        actions.pack(fill="x")
        button(actions,"Annulla",win.destroy,"ghost",width=125).pack(side="left")
        def submit():
            try:
                site=new_site(name.get(),url.get())
                if any(s["url"].casefold()==site["url"].casefold() for s in self.sites):
                    raise ValueError("Questo indirizzo è già in elenco.")
                if len(self.sites)>=100:
                    raise ValueError("Puoi monitorare fino a 100 siti.")
                candidates=self.sites+[site]
                save_sites(candidates)
            except (OSError,ValueError) as exc:
                messagebox.showerror("PolarWatch",str(exc),parent=win)
                return
            self.sites=candidates
            self.selected=site["id"]
            win.destroy()
            self.render()
            self.scan_selected()
        button(actions,"Aggiungi e controlla",submit,"primary",width=182).pack(side="right")
        url.bind("<Return>",lambda _:submit())
        name.focus_set()

    def remove_selected(self):
        site=self.selected_site()
        if site is None:
            self.set_notice("Seleziona un sito da rimuovere.","yellow")
            return
        if not messagebox.askyesno("Rimuovi sito",
                                   f"Rimuovere {site['name']} dall'elenco?\n"
                                   "Non viene cancellato alcun database.",
                                   parent=self.root):
            return
        candidates=[s for s in self.sites if s["id"]!=site["id"]]
        try:
            save_sites(candidates)
        except OSError as exc:
            messagebox.showerror("PolarWatch",str(exc),parent=self.root)
            return
        self.sites=candidates
        self.results.pop(site["id"],None)
        self.series.pop(site["id"],None)
        self.selected=self.sites[0]["id"] if self.sites else None
        self.render()
        self.set_notice("Sito rimosso.","green")

    def change_interval(self,choice):
        self.interval_seconds=0 if choice=="Off" else int(choice.split()[0])*60
        self.next_scan_at=(time.monotonic()+self.interval_seconds
                           if self.interval_seconds else float("inf"))
        self.interval_info.configure(
            text="○  Controlli in pausa" if not self.interval_seconds else f"●  Attivo · ogni {choice}",
            text_color=P["muted"] if not self.interval_seconds else P["green"])
        self.set_notice("Intervallo aggiornato.","muted")

    def toggle_expert(self):
        self.expert=bool(self.expert_switch.get())
        self._render_details()

    def scan_selected(self):
        site=self.selected_site()
        if not site:
            self.set_notice("Prima aggiungi o seleziona un sito.","yellow")
            return
        self._scan([site])

    def scan_all(self):
        if not self.sites:
            self.set_notice("Nessun sito: usa Aggiungi sito.","yellow")
            return
        self._scan(list(self.sites))

    def _scan(self,sites):
        if self.working:
            self.set_notice("Un controllo è già in corso.","yellow")
            return
        self.working=True
        self.set_notice(f"Verifica in corso · {len(sites)} siti…","cyan")
        self.checked_var.set("Controllo in corso…")
        self.scan_token+=1
        token=self.scan_token
        def work():
            try:
                with ThreadPoolExecutor(max_workers=min(4,len(sites))) as executor:
                    pending={executor.submit(probe_site,s,8):s for s in sites}
                    for future in as_completed(pending):
                        site=pending[future]
                        try:
                            result=future.result()
                        except Exception as exc:
                            result={
                                "id":site["id"],"name":site["name"],"url":site["url"],
                                "state":"DOWN","code":None,"latency":None,
                                "checked":time.strftime("%H:%M:%S"),
                                "ssl_days":None,"error":f"Diagnostica: {type(exc).__name__}",
                                "dns":[],"notes":[],"security_headers":{},
                            }
                        self.events.put(("result",token,result))
            finally:
                self.events.put(("done",token,len(sites)))
        threading.Thread(target=work,name="PolarWatch-Website-Probe",daemon=True).start()

    def poll(self):
        if self.closed:
            return
        changed=False
        try:
            while True:
                packet=self.events.get_nowait()
                kind,token,value=packet
                if token!=self.scan_token:
                    continue
                if kind=="result":
                    result=value
                    if not any(s["id"]==result["id"] for s in self.sites):
                        continue
                    self.results[result["id"]]=result
                    if result.get("state")=="UP" and isinstance(result.get("latency"),(int,float)):
                        history=self.series.setdefault(result["id"],[])
                        history.append(result["latency"])
                        del history[:-40]
                    changed=True
                elif kind=="done":
                    self.working=False
                    self.checked_var.set("Aggiornato alle "+time.strftime("%H:%M:%S"))
                    self.set_notice(f"Controllo completato · {value} siti verificati.","green")
                    self.next_scan_at=(time.monotonic()+self.interval_seconds
                                       if self.interval_seconds else float("inf"))
                    changed=True
        except queue.Empty:
            pass
        if changed:
            self.render()
        if self.sites and not self.working and self.interval_seconds:
            if time.monotonic()>=self.next_scan_at:
                self.scan_all()
        self._poll_after=self.root.after(280,self.poll)

    def copy_report(self):
        site=self.selected_site()
        if not site:
            self.set_notice("Seleziona un sito prima di copiare il report.","yellow")
            return
        r=self.results.get(site["id"])
        if not r:
            self.set_notice("Controlla il sito prima di copiare il report.","yellow")
            return
        points=[
            f"PolarWatch / PolarLabs — {site['name']}",
            f"URL: {site['url']}",
            f"Stato: {r.get('state')}  HTTP: {r.get('code') or '—'}",
            f"Latenza: {r.get('latency')} ms",
            f"TTFB: {r.get('ttfb')} ms",
            f"DNS: {', '.join(r.get('dns') or []) or '—'}",
            f"DNS lookup: {r.get('dns_ms')} ms",
            f"TLS: {r.get('tls') or '—'}",
            f"Certificato: {r.get('ssl_days')} giorni rimanenti",
            f"URL finale: {r.get('final_url') or '—'}",
            "Header di sicurezza presenti: "+
            (", ".join(k for k,v in (r.get("security_headers") or {}).items() if v) or "nessuno"),
            f"Note: {'; '.join(r.get('notes') or []) or 'nessuna'}",
            f"Errore: {r.get('error') or 'nessuno'}",
            "Risultati puntuali: non dimostrano la disponibilità continua.",
        ]
        self.root.clipboard_clear()
        self.root.clipboard_append("\n".join(points))
        self.root.update()
        self.set_notice("Report copiato negli appunti.","green")

    def close(self):
        self.closed=True
        callback=getattr(self,"_poll_after",None)
        if callback is not None:
            try:
                self.root.after_cancel(callback)
            except Exception:
                pass
        # CustomTkinter schedules DPI probes; cancel them as well before
        # destroying this Tk interpreter (important for repeated launches).
        try:
            for pending in self.root.tk.call("after", "info"):
                self.root.after_cancel(pending)
        except Exception:
            pass
        self.root.destroy()
