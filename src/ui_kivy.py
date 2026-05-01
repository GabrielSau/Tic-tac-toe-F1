from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.image import Image
from kivy.uix.widget import Widget
from kivy.core.window import Window
from kivy.graphics import Color, Rectangle, RoundedRectangle, Line, Ellipse, InstructionGroup
from kivy.animation import Animation
from kivy.clock import Clock
from kivy.metrics import dp, sp
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.relativelayout import RelativeLayout
from kivy.properties import StringProperty, BooleanProperty, ListProperty, NumericProperty

import os
import math
import requests
import threading

from src.logic import generate_grid, get_valid_drivers_for_cell
from src.database import SessionLocal, Driver

# ─── URL API Railway ──────────────────────────────────────────────────────────
API_URL = "https://tic-tac-toe-f1-production.up.railway.app" 

# Chemin absolu vers la racine du projet
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))

Window.size = (800, 1200)
Window.clearcolor = (0.05, 0.05, 0.07, 1)

# ─── Palette ──────────────────────────────────────────────────────────────────
C_BG          = (0.05, 0.05, 0.07, 1)
C_SURFACE     = (0.09, 0.09, 0.12, 1)
C_SURFACE2    = (0.12, 0.12, 0.16, 1)
C_RED         = (0.88, 0.12, 0.18, 1)
C_RED_DARK    = (0.55, 0.07, 0.10, 1)
C_GOLD        = (0.95, 0.78, 0.22, 1)
C_GOLD_DARK   = (0.60, 0.45, 0.10, 1)
C_WHITE       = (0.96, 0.96, 0.98, 1)
C_GREY        = (0.45, 0.45, 0.52, 1)
C_GREY_LIGHT  = (0.65, 0.65, 0.70, 1)
C_PLAYER_O    = (0.88, 0.12, 0.18, 1)
C_PLAYER_X    = (0.95, 0.78, 0.22, 1)
C_SUCCESS     = (0.18, 0.78, 0.45, 1)
C_BORDER      = (0.20, 0.20, 0.28, 1)


# ─── Helpers graphiques ───────────────────────────────────────────────────────

def _bg(widget, color, radius=0):
    """Dessine un fond coloré sur un widget avec canvas.before."""
    def _draw(w, *args):
        w.canvas.before.clear()
        with w.canvas.before:
            Color(*color)
            if radius:
                RoundedRectangle(pos=w.pos, size=w.size, radius=[radius])
            else:
                Rectangle(pos=w.pos, size=w.size)
    widget.bind(pos=_draw, size=_draw)
    _draw(widget)


def _border(widget, color, width=1.5, radius=8):
    """Dessine une bordure arrondie sur un widget."""
    def _draw(w, *args):
        w.canvas.after.clear()
        with w.canvas.after:
            Color(*color)
            Line(
                rounded_rectangle=(w.x, w.y, w.width, w.height, radius),
                width=width
            )
    widget.bind(pos=_draw, size=_draw)
    _draw(widget)


def _glow_border(widget, color, width=2.5, radius=10):
    """Bordure avec effet glow double couche."""
    def _draw(w, *args):
        w.canvas.after.clear()
        with w.canvas.after:
            Color(color[0], color[1], color[2], 0.25)
            Line(
                rounded_rectangle=(w.x - dp(3), w.y - dp(3),
                                   w.width + dp(6), w.height + dp(6), radius + 3),
                width=dp(4)
            )
            Color(*color)
            Line(
                rounded_rectangle=(w.x, w.y, w.width, w.height, radius),
                width=width
            )
    widget.bind(pos=_draw, size=_draw)
    _draw(widget)


# ─── Composants réutilisables ─────────────────────────────────────────────────

class Divider(Widget):
    def __init__(self, color=C_BORDER, **kwargs):
        super().__init__(size_hint_y=None, height=dp(1), **kwargs)
        def _draw(w, *args):
            w.canvas.clear()
            with w.canvas:
                Color(*color)
                Rectangle(pos=w.pos, size=w.size)
        self.bind(pos=_draw, size=_draw)
        _draw(self)


class StyledButton(Button):
    def __init__(self, bg=C_RED, text_color=C_WHITE, radius=dp(14), **kwargs):
        super().__init__(**kwargs)
        self._bg_color = bg
        self._bg_color_press = (
            max(0, bg[0] - 0.15),
            max(0, bg[1] - 0.05),
            max(0, bg[2] - 0.05),
            1
        )
        self.background_color = (0, 0, 0, 0)
        self.background_normal = ''
        self.background_down = ''
        self.color = text_color
        self._radius = radius
        self.font_size = sp(16)
        self.bold = True
        self.letter_spacing = sp(2)
        self._draw_bg(self._bg_color)
        self.bind(pos=lambda w, v: self._draw_bg(self._bg_color),
                  size=lambda w, v: self._draw_bg(self._bg_color))

    def _draw_bg(self, color):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*color)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[self._radius])

    def on_press(self):
        self._draw_bg(self._bg_color_press)
        anim = Animation(opacity=0.85, duration=0.05)
        anim.start(self)

    def on_release(self):
        self._draw_bg(self._bg_color)
        anim = Animation(opacity=1.0, duration=0.1)
        anim.start(self)


class PulsingDot(Widget):
    """Petit point qui pulse pour indiquer le tour actif."""
    def __init__(self, color, **kwargs):
        super().__init__(size_hint=(None, None), size=(dp(10), dp(10)), **kwargs)
        self._color = color
        self._alpha = 1.0
        self._draw()
        self.bind(pos=lambda w, v: self._draw(), size=lambda w, v: self._draw())
        self._start_pulse()

    def _draw(self):
        self.canvas.clear()
        with self.canvas:
            Color(self._color[0], self._color[1], self._color[2], self._alpha)
            Ellipse(pos=self.pos, size=self.size)

    def _start_pulse(self):
        def _pulse(dt):
            anim = (
                Animation(_alpha=0.3, duration=0.6) +
                Animation(_alpha=1.0, duration=0.6)
            )
            anim.bind(on_progress=lambda a, w, p: self._draw())
            anim.repeat = True
            anim.start(self)
        Clock.schedule_once(_pulse, 0.1)


class PlayerBadgeF1(BoxLayout):
    """Badge joueur style F1 avec image casque ou lettre + indicateur actif."""
    def __init__(self, player, active=False, **kwargs):
        super().__init__(
            orientation='vertical',
            spacing=0,
            **kwargs
        )
        self.player = player
        self.active = active
        col = C_PLAYER_O if player == "O" else C_PLAYER_X

        card_color = (
            col[0] * 0.10, col[1] * 0.10, col[2] * 0.10, 1
        ) if active else C_SURFACE2
        _bg(self, card_color, radius=dp(12))

        if active:
            _glow_border(self, col, width=dp(2), radius=dp(12))
        else:
            _border(self, C_BORDER, width=dp(1), radius=dp(12))

        header = BoxLayout(size_hint_y=None, height=dp(28),
                           padding=[dp(10), dp(4), dp(10), 0], spacing=dp(6))
        p_num = "P1" if player == "O" else "P2"
        p_lbl = Label(text=p_num, font_size=sp(11), bold=True,
                      color=col if active else C_GREY, halign='left', valign='middle')
        p_lbl.bind(size=p_lbl.setter('text_size'))
        header.add_widget(p_lbl)
        header.add_widget(Widget())

        if active:
            dot = PulsingDot(color=col)
            header.add_widget(dot)

        self.add_widget(header)

        helmet_area = FloatLayout(size_hint_y=1)
        img_path = os.path.normpath(os.path.join(
            _BASE_DIR, '..', 'img', f'Casque_{player}-removebg-preview.png'))
        if os.path.exists(img_path):
            img = Image(source=img_path, size_hint=(0.80, 0.80),
                        pos_hint={'center_x': 0.5, 'center_y': 0.5},
                        allow_stretch=True, keep_ratio=True, mipmap=True,
                        opacity=1.0 if active else 0.6)
            helmet_area.add_widget(img)
        else:
            lbl = Label(text=player, font_size=sp(32), bold=True,
                        color=col if active else (col[0]*0.6, col[1]*0.6, col[2]*0.6, 1),
                        pos_hint={'center_x': 0.5, 'center_y': 0.5})
            helmet_area.add_widget(lbl)
        self.add_widget(helmet_area)

        status_lbl = Label(
            text="À TOI DE JOUER" if active else "en attente",
            font_size=sp(9), bold=active,
            color=col if active else (C_GREY[0], C_GREY[1], C_GREY[2], 0.6),
            size_hint_y=None, height=dp(22), halign='center', valign='middle')
        status_lbl.bind(size=status_lbl.setter('text_size'))
        self.add_widget(status_lbl)


class GridCell(FloatLayout):
    """Case de la grille 3×3 avec image casque et effets glow."""
    def __init__(self, row, col, filled_player=None, on_tap=None, is_winning=False, **kwargs):
        super().__init__(**kwargs)
        self.row = row
        self.col = col

        if filled_player:
            player_color = C_PLAYER_O if filled_player == "O" else C_PLAYER_X
            # Fond coloré subtil
            _bg(self, (
                player_color[0] * 0.10,
                player_color[1] * 0.10,
                player_color[2] * 0.10,
                1
            ), radius=dp(12))
            if is_winning:
                _glow_border(self, player_color, width=dp(3), radius=dp(12))
            else:
                _border(self, player_color, width=dp(2), radius=dp(12))

            # Image du casque
            img_path = os.path.normpath(os.path.join(
                _BASE_DIR, '..', 'img',
                f'Casque_{filled_player}-removebg-preview.png'
            ))
            if os.path.exists(img_path):
                img = Image(
                    source=img_path,
                    size_hint=(0.72, 0.72),
                    pos_hint={'center_x': 0.5, 'center_y': 0.5},
                    allow_stretch=True,
                    keep_ratio=True,
                    mipmap=True
                )
                self.add_widget(img)
            else:
                lbl = Label(
                    text=filled_player,
                    font_size=sp(36),
                    bold=True,
                    color=player_color,
                    pos_hint={'center_x': 0.5, 'center_y': 0.5}
                )
                self.add_widget(lbl)

        else:
            # Case vide
            _bg(self, C_SURFACE2, radius=dp(12))
            _border(self, C_BORDER, width=dp(1.5), radius=dp(12))

            # Icône "+" discret
            plus = Label(
                text="+",
                font_size=sp(26),
                color=(C_GREY[0], C_GREY[1], C_GREY[2], 0.35),
                pos_hint={'center_x': 0.5, 'center_y': 0.5}
            )
            self.add_widget(plus)

            # Zone tactile invisible
            touch_btn = Button(
                background_color=(0, 0, 0, 0),
                background_normal='',
                size_hint=(1, 1),
                pos_hint={'x': 0, 'y': 0}
            )
            touch_btn.bind(on_press=lambda x: on_tap and on_tap(row, col))
            self.add_widget(touch_btn)


class HeaderBar(BoxLayout):
    """Barre de titre F1 premium."""
    def __init__(self, **kwargs):
        super().__init__(
            orientation='horizontal',
            size_hint_y=None,
            height=dp(72),
            padding=[dp(20), dp(10)],
            spacing=dp(12),
            **kwargs
        )
        _bg(self, C_SURFACE)

        accent = Widget(size_hint_x=None, width=dp(4))
        _bg(accent, C_RED)
        self.add_widget(accent)

        title_box = BoxLayout(orientation='vertical', spacing=0, padding=[dp(8), 0])
        title = Label(text="TIC-TAC-TOE", font_size=sp(22), bold=True, color=C_WHITE,
                      halign='left', valign='middle', size_hint_y=0.55)
        title.bind(size=title.setter('text_size'))
        subtitle = Label(text="FORMULA 1 EDITION", font_size=sp(10), color=C_RED,
                         halign='left', valign='middle', size_hint_y=0.45, bold=True)
        subtitle.bind(size=subtitle.setter('text_size'))
        title_box.add_widget(title)
        title_box.add_widget(subtitle)
        self.add_widget(title_box)
        self.add_widget(Widget())

        badge = BoxLayout(orientation='vertical', size_hint=(None, None), size=(dp(50), dp(50)))
        _bg(badge, C_RED, radius=dp(8))
        badge.add_widget(Label(text="F1", font_size=sp(20), bold=True, color=C_WHITE))
        self.add_widget(badge)


class TurnIndicator(BoxLayout):
    """Indicateur du tour actif avec images casques."""
    def __init__(self, current_player, **kwargs):
        super().__init__(orientation='horizontal', size_hint_y=None, height=dp(110),
                         padding=[dp(16), dp(8)], spacing=dp(12), **kwargs)
        _bg(self, C_SURFACE)

        for p in ["O", "X"]:
            is_active = (p == current_player)
            badge = PlayerBadgeF1(player=p, active=is_active, size_hint=(1, 1))
            self.add_widget(badge)
            if p == "O":
                vs_box = BoxLayout(orientation='vertical', size_hint_x=None, width=dp(36))
                vs_lbl = Label(text="VS", font_size=sp(12), bold=True,
                               color=(C_GREY[0], C_GREY[1], C_GREY[2], 0.5))
                vs_box.add_widget(vs_lbl)
                self.add_widget(vs_box)


class AxisLabel(Label):
    def __init__(self, text, **kwargs):
        super().__init__(text=text, font_size=sp(10), color=C_GREY_LIGHT,
                         markup=True, halign='center', valign='middle', **kwargs)
        self.bind(size=self.setter('text_size'))


# ─── Application principale ───────────────────────────────────────────────────

class TicTacToeF1App(App):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.grid_data = None
        self.selected_cell = None
        self.driver_candidates = []
        self.game_state = "menu"
        self.main_widget = None
        self.error_message = ""
        self.current_player = "O"
        self.filled_cells = {}
        self.winning_cells = []
        self.scores = {"O": 0, "X": 0}

        # ── Multijoueur en ligne ──────────────────────────────────────────────
        self.online_mode = False
        self.game_id = None
        self.my_player = None
        self._poll_event = None

    def build(self):
        self.main_widget = FloatLayout()
        _bg(self.main_widget, C_BG)
        self.show_menu()
        return self.main_widget

    # ── MENU ──────────────────────────────────────────────────────────────────

    def show_menu(self):
        self._stop_polling()
        self.online_mode = False
        self.game_id = None
        self.my_player = None

        self.main_widget.clear_widgets()
        self.game_state = "menu"
        _bg(self.main_widget, C_BG)

        root = BoxLayout(orientation='vertical', padding=[dp(30), dp(40)],
                         spacing=dp(20), size_hint=(1, 1), pos_hint={'x': 0, 'y': 0})

        logo_area = BoxLayout(orientation='vertical', size_hint_y=0.50, spacing=dp(12))
        helmets_row = BoxLayout(orientation='horizontal', size_hint_y=0.6,
                                spacing=dp(20), padding=[dp(60), 0])
        for player in ["O", "X"]:
            img_path = os.path.normpath(os.path.join(
                _BASE_DIR, '..', 'img', f'Casque_{player}-removebg-preview.png'))
            if os.path.exists(img_path):
                helmets_row.add_widget(Image(source=img_path, allow_stretch=True,
                                             keep_ratio=True, mipmap=True))
            else:
                helmets_row.add_widget(Label(text="🏎" if player == "O" else "🏁", font_size=sp(72)))
        logo_area.add_widget(helmets_row)

        title_lbl = Label(text="TIC-TAC-TOE", font_size=sp(42), bold=True,
                          color=C_WHITE, size_hint_y=0.22)
        logo_area.add_widget(title_lbl)

        sub_wrapper = BoxLayout(size_hint_y=0.18)
        sub_box = BoxLayout(size_hint_x=None, width=dp(280))
        _bg(sub_box, C_RED, radius=dp(5))
        sub_box.add_widget(Label(text="  FORMULA 1 EDITION  ", font_size=sp(14),
                                 bold=True, color=C_WHITE))
        sub_wrapper.add_widget(Widget())
        sub_wrapper.add_widget(sub_box)
        sub_wrapper.add_widget(Widget())
        logo_area.add_widget(sub_wrapper)
        root.add_widget(logo_area)

        if self.scores["O"] > 0 or self.scores["X"] > 0:
            score_card = BoxLayout(size_hint_y=None, height=dp(56),
                                   padding=[dp(20), dp(8)], spacing=dp(12))
            _bg(score_card, C_SURFACE2, radius=dp(10))
            _border(score_card, C_BORDER, radius=dp(10))
            for txt, col in [(f"O   {self.scores['O']}", C_PLAYER_O),
                              ("SCORE", C_GREY),
                              (f"{self.scores['X']}   X", C_PLAYER_X)]:
                lbl = Label(text=txt, font_size=sp(15), bold=True, color=col,
                            halign='center', valign='middle')
                lbl.bind(size=lbl.setter('text_size'))
                score_card.add_widget(lbl)
            root.add_widget(score_card)

        if self.error_message:
            err_card = BoxLayout(size_hint_y=None, height=dp(48), padding=[dp(16), dp(8)])
            _bg(err_card, (0.55, 0.07, 0.10, 0.85), radius=dp(8))
            err_card.add_widget(Label(text=f"⚠  {self.error_message[:60]}",
                                      font_size=sp(13), color=C_WHITE))
            root.add_widget(err_card)

        root.add_widget(Widget(size_hint_y=0.04))

        # ── Bouton partie locale ──────────────────────────────────────────────
        btn_play = StyledButton(text="PARTIE LOCALE", size_hint_y=None,
                                height=dp(64), bg=C_RED, font_size=sp(18))
        btn_play.bind(on_press=self.start_new_game)
        root.add_widget(btn_play)

        # ── Bouton créer partie en ligne ──────────────────────────────────────
        btn_create = StyledButton(text="CRÉER PARTIE EN LIGNE", size_hint_y=None,
                                  height=dp(56), bg=C_GOLD, text_color=(0.1, 0.1, 0.1, 1),
                                  font_size=sp(15))
        btn_create.bind(on_press=lambda x: self.create_online_game())
        root.add_widget(btn_create)

        # ── Bouton rejoindre partie ───────────────────────────────────────────
        btn_join = StyledButton(text="REJOINDRE UNE PARTIE", size_hint_y=None,
                                height=dp(56), bg=C_SURFACE2, text_color=C_GREY_LIGHT,
                                font_size=sp(15))
        btn_join.bind(on_press=lambda x: self.show_join_popup())
        root.add_widget(btn_join)

        btn_quit = StyledButton(text="QUITTER", size_hint_y=None, height=dp(52),
                                bg=C_SURFACE2, text_color=C_GREY_LIGHT, font_size=sp(15))
        btn_quit.bind(on_press=lambda x: self.stop())
        root.add_widget(btn_quit)

        root.add_widget(Widget(size_hint_y=0.05))
        root.add_widget(Label(text="Guess the F1 driver for each intersection",
                              font_size=sp(12),
                              color=(C_GREY[0], C_GREY[1], C_GREY[2], 0.65),
                              size_hint_y=None, height=dp(24)))

        self.main_widget.add_widget(root)

    # ── MULTIJOUEUR : CRÉER ───────────────────────────────────────────────────

    def create_online_game(self):
        def _do():
            try:
                r = requests.post(f"{API_URL}/game/create", timeout=5)
                data = r.json()
                Clock.schedule_once(lambda dt: self._on_game_created(data))
            except Exception as e:
                Clock.schedule_once(lambda dt: self._set_error(f"Connexion échouée: {e}"))

        threading.Thread(target=_do, daemon=True).start()

    def _on_game_created(self, data):
        self.game_id = data["game_id"]
        self.my_player = data["player"]
        self.online_mode = True
        self.scores = {"O": 0, "X": 0}
        self._show_waiting_screen()

    def _show_waiting_screen(self):
        self.main_widget.clear_widgets()
        _bg(self.main_widget, C_BG)

        root = BoxLayout(orientation='vertical', padding=[dp(40), dp(80)],
                         spacing=dp(24), size_hint=(1, 1), pos_hint={'x': 0, 'y': 0})

        root.add_widget(Label(text="PARTIE CRÉÉE", font_size=sp(28), bold=True, color=C_GOLD))

        root.add_widget(Label(text="Code de la partie :", font_size=sp(14), color=C_GREY_LIGHT))

        code_box = BoxLayout(size_hint_y=None, height=dp(72), padding=[dp(20), dp(10)])
        _bg(code_box, C_SURFACE2, radius=dp(12))
        _glow_border(code_box, C_GOLD, radius=dp(12))
        code_box.add_widget(Label(text=self.game_id, font_size=sp(32), bold=True, color=C_GOLD))
        root.add_widget(code_box)

        root.add_widget(Label(
            text="Donne ce code à ton adversaire.\nEn attente de la connexion...",
            font_size=sp(14), color=C_GREY_LIGHT, halign='center'))

        self._waiting_label = Label(text="⏳", font_size=sp(40), size_hint_y=None, height=dp(60))
        root.add_widget(self._waiting_label)

        btn_cancel = StyledButton(text="ANNULER", size_hint_y=None, height=dp(52),
                                  bg=C_SURFACE2, text_color=C_GREY_LIGHT, font_size=sp(14))
        btn_cancel.bind(on_press=lambda x: self.show_menu())
        root.add_widget(btn_cancel)

        self.main_widget.add_widget(root)
        self._start_polling()

    # ── MULTIJOUEUR : REJOINDRE ───────────────────────────────────────────────

    def show_join_popup(self):
        content = BoxLayout(orientation='vertical', padding=dp(20), spacing=dp(14))
        _bg(content, C_SURFACE)

        content.add_widget(Label(text="CODE DE LA PARTIE", font_size=sp(16),
                                 bold=True, color=C_WHITE, size_hint_y=None, height=dp(32)))

        inp = TextInput(multiline=False, font_size=sp(24), hint_text="ex: a1b2c3d4",
                        background_color=(0, 0, 0, 0), foreground_color=C_WHITE,
                        hint_text_color=(C_GREY[0], C_GREY[1], C_GREY[2], 0.6),
                        cursor_color=C_GOLD, size_hint_y=None, height=dp(56),
                        halign='center')
        _bg(inp, C_SURFACE2, radius=dp(10))
        content.add_widget(inp)

        btn_join = StyledButton(text="REJOINDRE", size_hint_y=None, height=dp(52),
                                bg=C_GOLD, text_color=(0.1, 0.1, 0.1, 1), font_size=sp(16))
        content.add_widget(btn_join)

        btn_cancel = StyledButton(text="ANNULER", size_hint_y=None, height=dp(44),
                                  bg=C_SURFACE2, text_color=C_GREY_LIGHT, font_size=sp(14))
        content.add_widget(btn_cancel)

        popup = Popup(title='', title_size=0, content=content, size_hint=(0.88, 0.45),
                      background='', background_color=(0, 0, 0, 0), separator_height=0)

        def _join(instance):
            gid = inp.text.strip()
            if not gid:
                return
            popup.dismiss()
            self._do_join(gid)

        btn_join.bind(on_press=_join)
        btn_cancel.bind(on_press=popup.dismiss)
        popup.open()

    def _do_join(self, game_id):
        def _req():
            try:
                r = requests.post(f"{API_URL}/game/join", json={"game_id": game_id}, timeout=5)
                if r.status_code == 200:
                    data = r.json()
                    Clock.schedule_once(lambda dt: self._on_joined(game_id, data))
                else:
                    Clock.schedule_once(lambda dt: self._set_error(f"Erreur: {r.json().get('detail', '?')}"))
            except Exception as e:
                Clock.schedule_once(lambda dt: self._set_error(f"Connexion échouée: {e}"))

        threading.Thread(target=_req, daemon=True).start()

    def _on_joined(self, game_id, data):
        self.game_id = game_id
        self.my_player = data["player"]
        self.online_mode = True
        self.scores = {"O": 0, "X": 0}
        self._start_polling()

    # ── POLLING ───────────────────────────────────────────────────────────────

    def _start_polling(self):
        self._stop_polling()
        self._poll_event = Clock.schedule_interval(self._poll_state, 1.5)

    def _stop_polling(self):
        if self._poll_event:
            Clock.unschedule(self._poll_event)
            self._poll_event = None

    def _poll_state(self, dt):
        def _fetch():
            try:
                r = requests.get(f"{API_URL}/game/{self.game_id}/state", timeout=3)
                state = r.json()
                Clock.schedule_once(lambda dt: self._apply_state(state))
            except Exception as e:
                print(f"Poll error: {e}")

        threading.Thread(target=_fetch, daemon=True).start()

    def _apply_state(self, state):
        prev_status = self.game_state

        # Récupère la grille dès qu'elle est dispo
        if state.get("grid") and self.grid_data is None:
            self.grid_data = state["grid"]

        # Convertit les clés "r_c" en tuples (r, c)
        self.filled_cells = {
            tuple(map(int, k.split("_"))): v
            for k, v in state["filled_cells"].items()
        }
        self.current_player = state["current_player"]
        self.scores = state["scores"]

        if state["status"] == "waiting":
            # Toujours en attente du 2e joueur
            return

        if state["status"] == "finished":
            self._stop_polling()
            winner = state.get("winner")
            is_draw = state.get("is_draw", False)
            if winner:
                self.winning_cells = self._get_winning_line(winner)
            self.show_result(winner=winner, is_draw=is_draw)
            return

        # status == "playing"
        if self.game_state != "playing" or prev_status == "waiting":
            self.game_state = "playing"

        self.show_game()

    # ── DÉMARRAGE PARTIE LOCALE ───────────────────────────────────────────────

    def start_new_game(self, instance=None):
        self._stop_polling()
        self.online_mode = False
        try:
            self.grid_data = generate_grid()
            self.selected_cell = None
            self.driver_candidates = []
            self.game_state = "playing"
            self.error_message = ""
            self.current_player = "O"
            self.filled_cells = {}
            self.winning_cells = []
            self.show_game()
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.error_message = str(e)[:60]
            self.show_menu()

    def _online_new_round(self):
        def _req():
            try:
                requests.post(f"{API_URL}/game/{self.game_id}/new_round", timeout=5)
            except Exception as e:
                print(f"new_round error: {e}")

        self.grid_data = None
        self.filled_cells = {}
        self.winning_cells = []
        threading.Thread(target=_req, daemon=True).start()
        self._start_polling()

    # ── JEU ───────────────────────────────────────────────────────────────────

    def show_game(self):
        if not self.grid_data:
            return

        self.main_widget.clear_widgets()
        _bg(self.main_widget, C_BG)

        root = BoxLayout(orientation='vertical', spacing=0,
                         size_hint=(1, 1), pos_hint={'x': 0, 'y': 0})

        root.add_widget(HeaderBar())
        root.add_widget(Divider(color=C_RED))

        # Bandeau "MON TOUR / EN ATTENTE" en mode online
        if self.online_mode:
            is_my_turn = (self.current_player == self.my_player)
            turn_color = C_GOLD if is_my_turn else C_GREY
            turn_text = f"▶  TON TOUR (Joueur {self.my_player})" if is_my_turn else "⏳  En attente de l'adversaire..."
            turn_banner = BoxLayout(size_hint_y=None, height=dp(36), padding=[dp(16), dp(6)])
            _bg(turn_banner,
                (C_GOLD[0]*0.12, C_GOLD[1]*0.12, C_GOLD[2]*0.12, 1) if is_my_turn else C_SURFACE)
            turn_banner.add_widget(Label(text=turn_text, font_size=sp(13), bold=True,
                                         color=turn_color, halign='left', valign='middle'))
            root.add_widget(turn_banner)

        root.add_widget(TurnIndicator(current_player=self.current_player))
        root.add_widget(Divider())

        grid_outer = BoxLayout(orientation='vertical', padding=[dp(12), dp(10)],
                               spacing=dp(6), size_hint_y=0.68)
        _bg(grid_outer, C_BG)

        col_header = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(6))
        col_header.add_widget(Widget(size_hint_x=None, width=dp(76)))
        for c in range(3):
            col_card = BoxLayout(padding=[dp(4), dp(4)])
            _bg(col_card, C_SURFACE, radius=dp(8))
            _border(col_card, C_BORDER, radius=dp(8))
            col_card.add_widget(AxisLabel(text=self.grid_data['cols'][c]['label']))
            col_header.add_widget(col_card)
        grid_outer.add_widget(col_header)

        for r in range(3):
            row_box = BoxLayout(spacing=dp(6))
            row_card = BoxLayout(size_hint_x=None, width=dp(76), padding=[dp(4), dp(4)])
            _bg(row_card, C_SURFACE, radius=dp(8))
            _border(row_card, C_BORDER, radius=dp(8))
            row_card.add_widget(AxisLabel(text=self.grid_data['rows'][r]['label']))
            row_box.add_widget(row_card)

            for c in range(3):
                player = self.filled_cells.get((r, c))
                is_win = (r, c) in self.winning_cells

                # En mode online : on bloque les cases si c'est pas notre tour
                if self.online_mode and self.current_player != self.my_player:
                    tap_cb = None
                else:
                    tap_cb = self.show_driver_picker

                cell = GridCell(row=r, col=c, filled_player=player,
                                on_tap=tap_cb, is_winning=is_win)
                row_box.add_widget(cell)
            grid_outer.add_widget(row_box)

        root.add_widget(grid_outer)

        score_bar = BoxLayout(size_hint_y=None, height=dp(44),
                              padding=[dp(20), dp(6)], spacing=dp(8))
        _bg(score_bar, C_SURFACE)
        o_count = sum(1 for p in self.filled_cells.values() if p == "O")
        x_count = sum(1 for p in self.filled_cells.values() if p == "X")
        empty = 9 - len(self.filled_cells)
        for txt, col in [(f"O: {o_count}", C_PLAYER_O),
                         (f"Cases libres: {empty}", C_GREY),
                         (f"X: {x_count}", C_PLAYER_X)]:
            score_bar.add_widget(Label(text=txt, font_size=sp(13), bold=True, color=col))
        root.add_widget(score_bar)

        btn_box = BoxLayout(size_hint_y=None, height=dp(58), padding=[dp(20), dp(8)])
        btn_menu = StyledButton(text="← MENU", bg=C_SURFACE2, text_color=C_GREY_LIGHT,
                                font_size=sp(14), size_hint_y=None, height=dp(42))
        btn_menu.bind(on_press=lambda x: self.show_menu())
        btn_box.add_widget(btn_menu)
        root.add_widget(btn_box)

        self.main_widget.add_widget(root)

    # ── PICKER PILOTE ─────────────────────────────────────────────────────────

    def show_driver_picker(self, row: int, col: int):
        self.selected_cell = (row, col)
        row_label = self.grid_data['rows'][row]['label']
        col_label = self.grid_data['cols'][col]['label']
        col_player = C_PLAYER_O if self.current_player == "O" else C_PLAYER_X

        content = BoxLayout(orientation='vertical', padding=dp(16), spacing=dp(10))
        _bg(content, C_SURFACE)

        header = BoxLayout(size_hint_y=None, height=dp(60), spacing=dp(8))
        img_path = os.path.normpath(os.path.join(
            _BASE_DIR, '..', 'img', f'Casque_{self.current_player}-removebg-preview.png'))
        if os.path.exists(img_path):
            header.add_widget(Image(source=img_path, size_hint=(None, 1), width=dp(48),
                                    allow_stretch=True, keep_ratio=True, mipmap=True))

        def _make_chip(text, col_accent):
            chip = BoxLayout(padding=[dp(10), dp(4)])
            _bg(chip, (col_accent[0]*0.15, col_accent[1]*0.15, col_accent[2]*0.15, 1), radius=dp(6))
            _border(chip, col_accent, width=dp(1), radius=dp(6))
            chip.add_widget(Label(text=text, font_size=sp(9), color=col_accent, markup=True))
            return chip

        chips = BoxLayout(orientation='vertical', spacing=dp(4))
        chips.add_widget(_make_chip(f"LIGNE  {row_label[:20]}", C_GOLD))
        chips.add_widget(_make_chip(f"COL  {col_label[:20]}", C_RED))
        header.add_widget(chips)
        content.add_widget(header)
        content.add_widget(Divider())

        player_indicator = BoxLayout(size_hint_y=None, height=dp(32),
                                     spacing=dp(8), padding=[dp(4), dp(4)])
        dot_bg = BoxLayout(size_hint_x=None, width=dp(24), size_hint_y=None, height=dp(24))
        _bg(dot_bg, col_player, radius=dp(12))
        dot_bg.add_widget(Label(text=self.current_player, font_size=sp(11), bold=True, color=C_WHITE))
        player_indicator.add_widget(dot_bg)
        player_indicator.add_widget(Label(
            text=f"JOUEUR {self.current_player} — choisissez un pilote",
            font_size=sp(11), color=col_player, halign='left', valign='middle'))
        content.add_widget(player_indicator)

        search_box = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(8), padding=[dp(12), dp(6)])
        _bg(search_box, C_SURFACE2, radius=dp(12))
        _border(search_box, C_BORDER, radius=dp(12))
        search_box.add_widget(Label(text="🔍", font_size=sp(18), size_hint_x=None, width=dp(30)))
        search_input = TextInput(
            multiline=False, font_size=sp(16), hint_text="Chercher un pilote F1...",
            background_color=(0, 0, 0, 0), foreground_color=C_WHITE,
            hint_text_color=(C_GREY[0], C_GREY[1], C_GREY[2], 0.8),
            cursor_color=col_player, size_hint_x=1)
        search_box.add_widget(search_input)
        content.add_widget(search_box)

        hint_lbl = Label(text="Tapez au moins 1 lettre", font_size=sp(11),
                         color=(C_GREY[0], C_GREY[1], C_GREY[2], 0.7),
                         size_hint_y=None, height=dp(20))
        content.add_widget(hint_lbl)

        scroll = ScrollView(size_hint_y=1)
        candidates_layout = BoxLayout(orientation='vertical', size_hint_y=None,
                                      spacing=dp(4), padding=[0, dp(4)])
        candidates_layout.bind(minimum_height=candidates_layout.setter('height'))
        scroll.add_widget(candidates_layout)
        content.add_widget(scroll)

        popup = Popup(title='', title_size=0, content=content, size_hint=(0.95, 0.78),
                      background='', background_color=(0, 0, 0, 0), separator_height=0)

        def _draw_popup_bg(w, *args):
            w.canvas.before.clear()
            with w.canvas.before:
                Color(*C_SURFACE)
                RoundedRectangle(pos=w.pos, size=w.size, radius=[dp(18)])
                Color(*col_player)
                Line(rounded_rectangle=(w.x, w.y, w.width, w.height, dp(18)), width=dp(1.5))
        popup.bind(pos=_draw_popup_bg, size=_draw_popup_bg)

        def on_search_text(instance, value):
            candidates_layout.clear_widgets()
            hint_lbl.text = "Tapez au moins 1 lettre" if len(value) < 1 else ""
            if len(value) < 1:
                return

            session = SessionLocal()
            results = session.query(Driver).filter(Driver.name.ilike(f"%{value}%")).limit(12).all()
            session.close()

            if not results:
                candidates_layout.add_widget(Label(
                    text="Aucun pilote trouvé", font_size=sp(14),
                    color=(C_GREY[0], C_GREY[1], C_GREY[2], 0.7),
                    size_hint_y=None, height=dp(44)))
                return

            for driver in results:
                rel = RelativeLayout(size_hint_y=None, height=dp(56))
                row_item = BoxLayout(size_hint=(1, 1), pos_hint={'x': 0, 'y': 0},
                                     padding=[dp(12), dp(6)], spacing=dp(12))
                _bg(row_item, C_SURFACE2, radius=dp(10))
                _border(row_item, C_BORDER, width=dp(1), radius=dp(10))

                initials = "".join(w[0].upper() for w in driver.name.split()[:2])
                circle = BoxLayout(size_hint=(None, None), size=(dp(38), dp(38)))
                _bg(circle, (col_player[0]*0.4, col_player[1]*0.4, col_player[2]*0.4, 1), radius=dp(19))
                _border(circle, col_player, width=dp(1.5), radius=dp(19))
                circle.add_widget(Label(text=initials, font_size=sp(13), bold=True, color=C_WHITE))
                row_item.add_widget(circle)

                name_lbl = Label(text=driver.name, font_size=sp(15), color=C_WHITE,
                                 halign='left', valign='middle')
                name_lbl.bind(size=name_lbl.setter('text_size'))
                row_item.add_widget(name_lbl)
                row_item.add_widget(Label(text="›", font_size=sp(24),
                                          color=(C_GREY[0], C_GREY[1], C_GREY[2], 0.5),
                                          size_hint_x=None, width=dp(24)))

                tap_btn = Button(background_color=(0, 0, 0, 0), background_normal='',
                                 size_hint=(1, 1), pos_hint={'x': 0, 'y': 0})
                tap_btn.bind(on_press=lambda x, d=driver, p=popup: (
                    self.validate_answer(d), p.dismiss()))
                rel.add_widget(row_item)
                rel.add_widget(tap_btn)
                candidates_layout.add_widget(rel)

        search_input.bind(text=on_search_text)

        btn_close = StyledButton(text="ANNULER", bg=C_SURFACE2, text_color=C_GREY_LIGHT,
                                 size_hint_y=None, height=dp(46), font_size=sp(14))
        btn_close.bind(on_press=popup.dismiss)
        content.add_widget(btn_close)
        popup.open()

    # ── VALIDATION ────────────────────────────────────────────────────────────

    def validate_answer(self, driver: Driver):
        if not self.selected_cell or not self.grid_data:
            return

        if self.online_mode:
            # Envoie le coup à l'API
            r, c = self.selected_cell
            payload = {
                "game_id": self.game_id,
                "player": self.my_player,
                "row": r, "col": c,
                "driver_id": driver.id
            }
            def _send():
                try:
                    requests.post(f"{API_URL}/game/play", json=payload, timeout=5)
                except Exception as e:
                    print(f"play error: {e}")
            threading.Thread(target=_send, daemon=True).start()
            # Le polling mettra à jour l'état automatiquement
            return

        # ── Mode local ────────────────────────────────────────────────────────
        r, c = self.selected_cell
        row_crit = self.grid_data['rows'][r]
        col_crit = self.grid_data['cols'][c]
        valid_ids = get_valid_drivers_for_cell(row_crit, col_crit)

        if driver.id in valid_ids:
            self.filled_cells[(r, c)] = self.current_player
            winner = self.check_winner()
            if winner:
                self.winning_cells = self._get_winning_line(winner)
                self.scores[winner] += 1
                self.show_result(winner=winner, is_draw=False)
            elif len(self.filled_cells) == 9:
                self.show_result(winner=None, is_draw=True)
            else:
                self.current_player = "X" if self.current_player == "O" else "O"
                self.show_game()
        else:
            self.current_player = "X" if self.current_player == "O" else "O"
            self.show_game()

    def check_winner(self) -> str:
        for r in range(3):
            if all((r, c) in self.filled_cells and self.filled_cells[(r, c)] == self.current_player for c in range(3)):
                return self.current_player
        for c in range(3):
            if all((r, c) in self.filled_cells and self.filled_cells[(r, c)] == self.current_player for r in range(3)):
                return self.current_player
        if all((i, i) in self.filled_cells and self.filled_cells[(i, i)] == self.current_player for i in range(3)):
            return self.current_player
        if all((i, 2-i) in self.filled_cells and self.filled_cells[(i, 2-i)] == self.current_player for i in range(3)):
            return self.current_player
        return None

    def _get_winning_line(self, player) -> list:
        for r in range(3):
            if all((r, c) in self.filled_cells and self.filled_cells[(r, c)] == player for c in range(3)):
                return [(r, c) for c in range(3)]
        for c in range(3):
            if all((r, c) in self.filled_cells and self.filled_cells[(r, c)] == player for r in range(3)):
                return [(r, c) for r in range(3)]
        if all((i, i) in self.filled_cells and self.filled_cells[(i, i)] == player for i in range(3)):
            return [(i, i) for i in range(3)]
        if all((i, 2-i) in self.filled_cells and self.filled_cells[(i, 2-i)] == player for i in range(3)):
            return [(i, 2-i) for i in range(3)]
        return []

    # ── RÉSULTAT ──────────────────────────────────────────────────────────────

    def show_result(self, winner, is_draw):
        self._stop_polling()
        self.main_widget.clear_widgets()
        _bg(self.main_widget, C_BG)

        root = BoxLayout(orientation='vertical', padding=[dp(30), dp(40)],
                         spacing=dp(20), size_hint=(1, 1), pos_hint={'x': 0, 'y': 0})
        root.add_widget(Widget(size_hint_y=0.04))

        helmet_area = BoxLayout(orientation='horizontal', size_hint_y=0.32, padding=[dp(40), 0])
        if is_draw:
            for p in ["O", "X"]:
                img_path = os.path.normpath(os.path.join(
                    _BASE_DIR, '..', 'img', f'Casque_{p}-removebg-preview.png'))
                if os.path.exists(img_path):
                    helmet_area.add_widget(Image(source=img_path, allow_stretch=True,
                                                 keep_ratio=True, mipmap=True))
        else:
            img_path = os.path.normpath(os.path.join(
                _BASE_DIR, '..', 'img', f'Casque_{winner}-removebg-preview.png'))
            if os.path.exists(img_path):
                helmet_area.add_widget(Widget(size_hint_x=0.2))
                helmet_area.add_widget(Image(source=img_path, allow_stretch=True,
                                             keep_ratio=True, mipmap=True))
                helmet_area.add_widget(Widget(size_hint_x=0.2))
            else:
                helmet_area.add_widget(Label(text="🏆", font_size=sp(80)))
        root.add_widget(helmet_area)

        result_card = BoxLayout(orientation='vertical', size_hint_y=None, height=dp(140),
                                padding=[dp(20), dp(20)], spacing=dp(8))
        if is_draw:
            accent_color = C_GOLD
            main_text = "MATCH NUL"
            sub_text = "Personne ne remporte le Grand Prix"
        else:
            accent_color = C_PLAYER_O if winner == "O" else C_PLAYER_X
            main_text = f"JOUEUR {winner} GAGNE !"
            sub_text = "Victoire au Grand Prix — Podium P1 🏅"

        _bg(result_card, (accent_color[0]*0.12, accent_color[1]*0.12, accent_color[2]*0.12, 1), radius=dp(18))
        _glow_border(result_card, accent_color, width=dp(2.5), radius=dp(18))
        result_card.add_widget(Label(text=main_text, font_size=sp(32), bold=True,
                                     color=accent_color, size_hint_y=0.6))
        result_card.add_widget(Label(text=sub_text, font_size=sp(13),
                                     color=C_GREY_LIGHT, size_hint_y=0.4))
        root.add_widget(result_card)

        score_card = BoxLayout(size_hint_y=None, height=dp(52),
                               padding=[dp(20), dp(8)], spacing=dp(12))
        _bg(score_card, C_SURFACE2, radius=dp(10))
        for txt, col in [(f"O  {self.scores['O']}", C_PLAYER_O),
                         ("TOTAL", C_GREY),
                         (f"{self.scores['X']}  X", C_PLAYER_X)]:
            score_card.add_widget(Label(text=txt, font_size=sp(16), bold=True, color=col))
        root.add_widget(score_card)
        root.add_widget(Widget(size_hint_y=0.05))

        btn_replay = StyledButton(text="NOUVELLE COURSE", size_hint_y=None, height=dp(62),
                                  bg=C_RED, font_size=sp(17))
        if self.online_mode:
            btn_replay.bind(on_press=lambda x: self._online_new_round())
        else:
            btn_replay.bind(on_press=lambda x: self.start_new_game())
        root.add_widget(btn_replay)

        btn_menu = StyledButton(text="RETOUR AU MENU", size_hint_y=None, height=dp(52),
                                bg=C_SURFACE2, text_color=C_GREY_LIGHT, font_size=sp(15))
        btn_menu.bind(on_press=lambda x: self.show_menu())
        root.add_widget(btn_menu)

        self.main_widget.add_widget(root)

    # ── ERREUR ────────────────────────────────────────────────────────────────

    def _set_error(self, msg):
        self.error_message = msg
        self.show_menu()

    def show_error(self, message: str):
        content = BoxLayout(orientation='vertical', padding=dp(16), spacing=dp(12))
        _bg(content, C_SURFACE)
        content.add_widget(Label(text=message, font_size=sp(15), color=C_WHITE, size_hint_y=0.7))
        btn = StyledButton(text="OK", size_hint_y=None, height=dp(44), bg=C_RED)
        content.add_widget(btn)
        popup = Popup(title='', title_size=0, content=content, size_hint=(0.88, 0.35),
                      background='', background_color=(0, 0, 0, 0), separator_height=0)
        btn.bind(on_press=popup.dismiss)
        popup.open()


if __name__ == "__main__":
    app = TicTacToeF1App()
    app.run()