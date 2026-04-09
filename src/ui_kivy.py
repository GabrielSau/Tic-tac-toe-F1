from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.image import Image
from kivy.core.window import Window

from src.logic import generate_grid, get_valid_drivers_for_cell
from src.database import SessionLocal, Driver

Window.size = (800, 1200)


class TicTacToeF1App(App):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.grid_data = None
        self.selected_cell = None
        self.driver_candidates = []
        self.game_state = "menu"
        self.main_widget = None
        self.error_message = ""
        self.current_player = "O"  # Joueur O ou X
        self.filled_cells = {}  # {(r,c): "O" ou "X"}
    
    def build(self):
        self.main_widget = BoxLayout(orientation='vertical', padding=10, spacing=10)
        self.show_menu()
        return self.main_widget
    
    def show_menu(self):
        """Affiche le menu principal"""
        self.main_widget.clear_widgets()
        self.game_state = "menu"
        
        layout = BoxLayout(orientation='vertical', padding=20, spacing=20)
        
        title = Label(text="Tic-Tac-Toe F1", size_hint_y=0.2, font_size='48sp', bold=True)
        layout.add_widget(title)
        
        # Afficher les erreurs s'il y en a
        if self.error_message:
            error_label = Label(text=self.error_message, size_hint_y=0.2, font_size='14sp', color=(1, 0.2, 0.2, 1))
            layout.add_widget(error_label)
        
        spacer = Label(size_hint_y=0.3)
        layout.add_widget(spacer)
        
        btn_new_game = Button(text="Nouvelle Partie", size_hint_y=0.15, font_size='24sp')
        btn_new_game.bind(on_press=self.start_new_game)
        layout.add_widget(btn_new_game)
        
        btn_quit = Button(text="Quitter", size_hint_y=0.15, font_size='18sp')
        btn_quit.bind(on_press=lambda x: self.stop())
        layout.add_widget(btn_quit)
        
        self.main_widget.add_widget(layout)
    
    def start_new_game(self, instance=None):
        """Lance une nouvelle partie"""
        try:
            print("🎮 Génération de la grille...")
            self.grid_data = generate_grid()
            self.selected_cell = None
            self.driver_candidates = []
            self.game_state = "playing"
            self.error_message = ""
            self.current_player = "O"  # Commencer avec le joueur O
            self.filled_cells = {}  # Réinitialiser les cases remplies
            self.show_game()
        except Exception as e:
            print(f"❌ Erreur: {str(e)}")
            import traceback
            traceback.print_exc()
            self.error_message = f"Erreur: {str(e)[:50]}..."
            self.show_menu()
    
    def show_game(self):
        """Affiche le jeu avec grille 3x3"""
        self.main_widget.clear_widgets()
        
        main_layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        # Afficher le joueur actuel avec son image
        player_section = BoxLayout(size_hint_y=0.1, spacing=10)
        player_label = Label(text=f"Joueur {self.current_player}:", size_hint_x=0.5, font_size='16sp')
        
        # Image du casque du joueur actuel
        casque_image = Image(
            source=f'img/Casque_{self.current_player}-removebg-preview.png',
            size_hint_x=0.5
        )
        player_section.add_widget(player_label)
        player_section.add_widget(casque_image)
        main_layout.add_widget(player_section)
        
        # Grille 3x3
        grid_container = BoxLayout(size_hint_y=0.8, spacing=2)
        
        # Colonne gauche: labels des lignes
        left_labels = BoxLayout(orientation='vertical', size_hint_x=0.25, spacing=2)
        left_labels.add_widget(Label(text="", size_hint_y=0.33))  # Coin vide
        for r in range(3):
            label = Label(
                text=self.grid_data['rows'][r]['label'],
                size_hint_y=0.33,
                font_size='10sp',
                markup=True
            )
            left_labels.add_widget(label)
        grid_container.add_widget(left_labels)
        
        # Grille principale
        grid_main = BoxLayout(orientation='vertical', size_hint_x=0.75, spacing=2)
        
        # Ligne supérieure: labels des colonnes
        top_labels = BoxLayout(size_hint_y=0.15, spacing=2)
        for c in range(3):
            label = Label(
                text=self.grid_data['cols'][c]['label'],
                font_size='10sp',
                markup=True
            )
            top_labels.add_widget(label)
        grid_main.add_widget(top_labels)
        
        # Grille 3x3
        grid_layout = GridLayout(cols=3, rows=3, spacing=2, size_hint_y=0.85)
        
        for r in range(3):
            for c in range(3):
                if (r, c) in self.filled_cells:
                    # Case remplie: afficher l'image du casque
                    player = self.filled_cells[(r, c)]
                    btn = Image(
                        source=f'img/Casque_{player}-removebg-preview.png',
                        size_hint=(1, 1)
                    )
                else:
                    # Case vide: bouton cliquable
                    btn = Button(
                        background_color=(0.2, 0.2, 0.4, 1),
                        border=(2, 2, 2, 2)
                    )
                    btn.bind(on_press=lambda x, row=r, col=c: self.show_driver_picker(row, col))
                
                grid_layout.add_widget(btn)
        
        grid_main.add_widget(grid_layout)
        grid_container.add_widget(grid_main)
        main_layout.add_widget(grid_container)
        
        # Bouton retour au menu
        btn_menu = Button(text="Menu", size_hint_y=0.1, font_size='16sp')
        btn_menu.bind(on_press=lambda x: self.show_menu())
        main_layout.add_widget(btn_menu)
        
        self.main_widget.add_widget(main_layout)
    
    def show_driver_picker(self, row: int, col: int):
        """Affiche une popup pour chercher et sélectionner un pilote"""
        self.selected_cell = (row, col)
        self.driver_candidates = []
        
        r, c = self.selected_cell
        row_label = self.grid_data['rows'][r]['label']
        col_label = self.grid_data['cols'][c]['label']
        
        # Contenu de la popup
        content = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        # Titre avec les catégories
        title_label = Label(
            text=f"Ligne: {row_label}\nColonne: {col_label}",
            size_hint_y=0.15,
            font_size='12sp'
        )
        content.add_widget(title_label)
        
        # Champ de recherche
        search_input = TextInput(
            multiline=False,
            font_size='16sp',
            hint_text="Chercher un pilote...",
            size_hint_y=0.1
        )
        content.add_widget(search_input)
        
        # Liste des candidats
        scroll = ScrollView(size_hint_y=0.65)
        candidates_layout = BoxLayout(orientation='vertical', size_hint_y=None, spacing=3)
        candidates_layout.bind(minimum_height=candidates_layout.setter('height'))
        scroll.add_widget(candidates_layout)
        content.add_widget(scroll)
        
        # Créer la popup
        popup = Popup(
            title=f"Sélectionner un pilote",
            content=content,
            size_hint=(0.95, 0.8)
        )
        
        def on_search_text(instance, value):
            """Filtre les candidats en temps réel"""
            candidates_layout.clear_widgets()
            
            if len(value) < 1:
                return
            
            session = SessionLocal()
            results = session.query(Driver).filter(
                Driver.name.ilike(f"%{value}%")
            ).limit(15).all()
            session.close()
            
            for driver in results:
                btn = Button(
                    text=f"{driver.name}",
                    size_hint_y=None,
                    height=40,
                    font_size='14sp',
                    background_color=(0.2, 0.5, 0.2, 1)
                )
                
                def on_driver_select(x, d=driver, p=popup):
                    self.validate_answer(d)
                    p.dismiss()
                
                btn.bind(on_press=on_driver_select)
                candidates_layout.add_widget(btn)
        
        search_input.bind(text=on_search_text)
        
        # Bouton fermer
        btn_close = Button(text="Fermer", size_hint_y=0.1, font_size='14sp')
        btn_close.bind(on_press=popup.dismiss)
        content.add_widget(btn_close)
        
        popup.open()
    
    def validate_answer(self, driver: Driver):
        """Valide la réponse du joueur"""
        if not self.selected_cell or not self.grid_data:
            return
        
        r, c = self.selected_cell
        row_crit = self.grid_data['rows'][r]
        col_crit = self.grid_data['cols'][c]
        valid_ids = get_valid_drivers_for_cell(row_crit, col_crit)
        
        if driver.id in valid_ids:
            # Réponse correcte : marquer la case et passer au joueur suivant
            self.filled_cells[(r, c)] = self.current_player
            
            # Vérifier si c'est un tic-tac-toe (gagnant)
            winner = self.check_winner()
            
            if winner:
                # Un joueur a gagné !
                self.show_result(f"Joueur {winner} a gagné !", True)
            elif len(self.filled_cells) == 9:
                # Grille pleine : match nul
                self.show_result("Egalité !", False)
            else:
                # Continuer : passer au joueur suivant
                self.current_player = "X" if self.current_player == "O" else "O"
                self.show_game()
        else:
            # Réponse incorrecte : juste passer au joueur suivant sans afficher "incorrect"
            self.current_player = "X" if self.current_player == "O" else "O"
            self.show_game()
    
    def check_winner(self) -> str:
        """Vérifie s'il y a un gagnant (ligne, colonne ou diagonale)"""
        # Lignes
        for r in range(3):
            if all((r, c) in self.filled_cells and self.filled_cells[(r, c)] == self.current_player for c in range(3)):
                return self.current_player
        
        # Colonnes
        for c in range(3):
            if all((r, c) in self.filled_cells and self.filled_cells[(r, c)] == self.current_player for r in range(3)):
                return self.current_player
        
        # Diagonale principale
        if all((i, i) in self.filled_cells and self.filled_cells[(i, i)] == self.current_player for i in range(3)):
            return self.current_player
        
        # Diagonale inversée
        if all((i, 2-i) in self.filled_cells and self.filled_cells[(i, 2-i)] == self.current_player for i in range(3)):
            return self.current_player
        
        return None
    
    def show_result(self, message: str, is_correct: bool):
        """Affiche le résultat de la partie"""
        self.main_widget.clear_widgets()
        
        layout = BoxLayout(orientation='vertical', padding=20, spacing=20)
        
        result_label = Label(text=message, size_hint_y=0.5, font_size='32sp')
        layout.add_widget(result_label)
        
        btn_continue = Button(text="Nouvelle Partie", size_hint_y=0.2, font_size='24sp')
        btn_continue.bind(on_press=lambda x: self.start_new_game())
        layout.add_widget(btn_continue)
        
        btn_menu = Button(text="Menu", size_hint_y=0.2, font_size='18sp')
        btn_menu.bind(on_press=lambda x: self.show_menu())
        layout.add_widget(btn_menu)
        
        self.main_widget.add_widget(layout)
    
    def show_error(self, message: str):
        """Affiche un message d'erreur"""
        content = BoxLayout(orientation='vertical', padding=10, spacing=10)
        content.add_widget(Label(text=message, font_size='16sp'))
        
        btn_close = Button(text="OK", size_hint_y=0.2, font_size='18sp')
        content.add_widget(btn_close)
        
        popup = Popup(title='Erreur', content=content, size_hint=(0.9, 0.5))
        btn_close.bind(on_press=popup.dismiss)
        popup.open()


if __name__ == "__main__":
    app = TicTacToeF1App()
    app.run()
