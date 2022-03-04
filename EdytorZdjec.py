import tkinter as tk
import tkinter.messagebox, tkinter.filedialog
import configparser
import PIL as pil
from PIL import Image, ImageTk, ImageFilter, ImageChops, ImageOps, ImageEnhance
import exif
import piexif

config_file = "config.txt"

class Gui(tk.Frame):
    """
    Główna klasa aplikacji odpowiedzialna za konstrukcje Gui oraz obsługę wszystkich funkcji
    modyfikacji obrazu oraz odczytywanie i modyfikację danych EXIF
    """
    def __init__(self, master=None):
        """
        Główny konstruktor gui aplikacji.
        :param master:
        """

        self.config_data = configparser.ConfigParser()
        self.config_data.read(config_file, "UTF8")
        tk.Frame.__init__(self, master)

        self.parent = master
        self.parent.title("Edytor zdjęć")
        self.parent.protocol("WM_DELETE_WINDOW", self.appQuit)

        default_settings = self.config_data["DEFAULT"]
        self.base_geometry = default_settings.get("base_geometry", "1000x800+50+50")
        self.parent.geometry(self.base_geometry)

        self.picture = None
        self.picture_starting_size = None
        self.proportions = None
        self.picture_copy = self.picture
        self.picture_path = None
        self.picture_TkImage = None
        self.picture_EXIF = None
        self.has_exif = False
        self.exif_dict = None
        self.moves_list = []
        self.current_move = 0

        self.createMenuBar()
        self.createWorkSpace()
        self.create_status()
        self.createToolBar()

        self.parent.columnconfigure(0, weight=999)
        self.parent.columnconfigure(1, weight=1)
        self.parent.rowconfigure(0, weight=1)
        self.parent.rowconfigure(1, weight=9999)
        self.parent.rowconfigure(2, weight=1)

        self.screen.bind('<Configure>', self.resizeImage)

    def appQuit(self, event=None):
        """
        Metoda odpowiedzialna za zamykanie aplikacji.
        :param event: użycie skrótu klawiszowego przypisanego do aplikacji
        :return:
        """
        if self.picture != None and len(self.moves_list) > 0:
            reply = tk.messagebox.askyesno("Otwarty plik", "Otwarty jest plik, czy chcesz go zapisać?")
            if reply:
                self.saveFile()


        reply = tkinter.messagebox.askyesno("Zakończenie pracy programu.", "Czy na pewno chcesz zakończyć pracę programu?",parent= self.parent)
        event = event
        if reply:
            self.parent.destroy()

    def create_status(self):
        """
        Metoda odpowiedzialna za utworzenie paska statusu.
        :return:
        """
        self.stausbar = tk.Label(self.parent, text="status...", anchor=tk.W)
        self.stausbar.after(5000, self.clearStatusBar)
        self.stausbar.grid(row=2, column=0, columnspan=2, sticky=tk.EW)

    def clearStatusBar(self):
        """
        Metoda służąca do czyszczenia pasku statusu.
        :return:
        """
        self.stausbar["text"] = ""

    def setStatusBar(self, txt):
        """
        Metoda służąca do ustawiania pasku statusu.
        :param txt: ciąg znaków ustawiany jako status
        :return:
        """
        self.stausbar["text"] = txt

    def createMenuBar(self):
        """
        Metoda służąca do utworzenia paska menu razem ze wszystkimi podmenu oraz przyporządkowanie
        skrótów klawiszowych do funkcjonalności aplikacji.
        :return:
        """
        self.menubar = tk.Menu(self.parent)
        self.parent["menu"] = self.menubar
        fileMenu = tk.Menu(self.menubar)

        for label, command, shortcut_text, shortcut in (
                ("Wybierz plik", self.chooseFile, "Ctrl+O", "<Control-o>"),
                ("Zapisz plik", self.saveFile, "Ctrl+S", "<Control-s>"),
                ("Zapisz jako...", self.saveFileAs, "Ctrl+A", "<Control-a>"),
                ("Cofnij działanie", self.goBack, "Ctrl+Z", "<Control-z>"),
                ("Następne działanie", self.goForward, "Ctrl+X", "<Control-x>"),
                (None, None, None, None),
                ("Wyjdź", self.appQuit, "Ctrl+Q", "<Control-q>")):
            if label is None:
                fileMenu.add_separator()
            else:
                fileMenu.add_command(label=label, underline=0, command=command, accelerator=shortcut_text)
                self.parent.bind(shortcut, command)
        self.menubar.add_cascade(label="Plik", menu=fileMenu, underline=0)

        editionmenu = tk.Menu(self.menubar)

        for label, command, shortcut_text, shortcut in (
            ("Jasność", self.changeBrightness, "Ctrl+B", "<Control-b>"),
            ("Ostrość", self.changeSharpness, "Ctrl+N", "<Control-n>"),
            ("Kontrast", self.changeContrast, "Ctrl+K", "<Control-k>"),
            ("Kolory nasycenie", self.changeColourSat, "Ctrl+M", "<Control-m>"),
            ("Połącz z..", self.blendWithImage, None, None),
            ("Odwróć kolory", self.invertImage, None, None),
            ("Różnice między pikselami", self.diffrence, None, None),
            ("Skaluj", self.scaleImage, None, None),
            ("Posteryzuj", self.posterizeImage, None, None),
            (None, None, None, None),
            ("Obrót w lewo", self.RotateToLeft, None, None),
            ("Obrót w prawo", self.RotateToRight, None, None),
            ("Obrót w prawo o..", self.rotateToRightDeg, None, None),
            ("Obrót w lewo o..", self.rotateToLeftDeg, None, None),
            ("Odwróć w poziomie", self.flipLeftRigth, None, None),
            ("Odwróć w pionie", self.flipTopBottom, None, None)
        ):

            if label is None:
                editionmenu.add_separator()
            else:
                if shortcut_text is None:
                    editionmenu.add_command(label=label, underline=0, command=command)
                else:
                    editionmenu.add_command(label=label, underline=0, command=command, accelerator=shortcut_text)
                    self.parent.bind(shortcut, command)
        self.menubar.add_cascade(label="Edycja", menu=editionmenu, underline=0)

        exifMenu = tk.Menu(self.menubar)

        for label, command, shortcut_text, shortcut in (
                ("Wyświetl dane exif", self.showExif, "Ctrl+E", "<Control-e>"),
                ("Modyfikuj dane exif", self.changeExif, "Ctrl+R", "<Control-r>"),
                ("Zapisz dane exif", self.saveEXIF, "Ctrl+F", "<Control-f>"),
                ("Wyświetl lokalizacje zdjecia", self.showPhotoLocation, "Ctrl+L", "<Control-l>"),
                (None, None, None, None),
                ("Usuń dane exif", self.deleteEXIF, "Ctrl+D", "<Control-d>")
        ):
            if label is None:
                fileMenu.add_separator()
            else:
                if shortcut_text is None:
                    exifMenu.add_command(label=label, underline=0, command=command)
                else:
                    exifMenu.add_command(label=label, underline=0, command=command, accelerator=shortcut_text)
                    self.parent.bind(shortcut, command)
        self.menubar.add_cascade(label="EXIF", menu=exifMenu, underline=0)

        filterMenu = tk.Menu(self.menubar)

        for label, command in (
                ("BLUR", self.blurFilter),
                ("Czarno-Biały (grayscale)", self.grayscale),
                ("Kontury", self.contourfilter),
                ("Detale", self.detailFilter),
                ("Poprawione krawędzie", self.edgeEnchFilter),
                ("Poprwaione krawędzie 2", self.edgeEnchMFilter),
                ("EMBOSS", self.embossFilter),
                ("Znajdź krawędzie", self.findEdgesFilter),
                ("Wyostrz", self.sharpenFilter),
                ("Wygładź", self.smoothFilter),
                ("Wygładź 2", self.smoothMFilter),
                ("Ramka Hexagon", self.hexagonFrameFilter)
        ):
            if label is None:
                fileMenu.add_separator()
            else:
                filterMenu.add_command(label=label, underline=0, command=command)
        self.menubar.add_cascade(label="Filtry", menu=filterMenu, underline=0)

    def createToolBar(self):
        """
        Metoda służąca do utworzenia paska narzędzi i przycisków znajdujących się na nim.
        :return:
        """
        self.toolBar = tk.Frame(self.parent)
        self.button_number = 0

        for name, command in (
                ("Cofnij", self.goBack),
                ("Następny", self.goForward),
                ("Prawo", self.RotateToRight),
                ("Lewo", self.RotateToLeft)
        ):
            button = tk.Button(self.toolBar, text=name, command=command)
            button.grid(row=0, column=self.button_number, columnspan=2, sticky=tk.NSEW)
            self.button_number += 2
        self.toolBar.grid(row=0, column=0, columnspan=10, sticky=tk.EW)

    def createWorkSpace(self):
        """
        Metoda służąca do utworzenia przestrzeni roboczej na której wyświetlane będzie zdjęcie.
        :return:
        """
        self.workSpace = tk.Frame(self.parent, background="gray")
        self.workSpace.grid(row=0, column=0, columnspan=1, rowspan=80, sticky=tk.NSEW)
        self.screen = tk.Label(self.workSpace)
        self.screen.pack(fill='both', expand=True)

    def saveFile(self, event=None):
        """
        Metoda służąca do zapisania aktualnie modyfikowanego obrazu do pliku z którego został otwarty.
        :param event: użycie skrótu klawiszowego przypisanego do metody
        :return:
        """
        if self.__pictureIsNotNone():
            try:

                if self.has_exif:
                    exif_dict = piexif.load(self.picture.info["exif"])
                    exif_bytes = piexif.dump(exif_dict)
                    self.picture.save(self.picture_path, exif=exif_bytes)
                else:
                    self.picture.save(self.picture_path)
                self.resetQueue()
            except ValueError:
                tk.messagebox.showerror("Błąd zapisu","Nastąpił błąd podczas zapisywania do pliku.")

    def saveFileAs(self, event=None):
        """
        Metoda służąca do zapisania aktualnie modyfikowanego obrazu do pliku wybranego lub utworzonego
        przez użytkownika w oknie dialogowym.
        :param event: użycie skrótu klawiszowego przypisanego do metody
        :return:
        """
        if self.__pictureIsNotNone():
            save_path = tk.filedialog.asksaveasfilename(filetypes=[
                ("JPG files", ".jpg"),
                ("PNG files", ".png"),
                ("Other files", ".*")],
                defaultextension=".jpg")
            try:
                if self.has_exif:
                    exif_dict = piexif.load(self.picture.info["exif"])
                    exif_bytes = piexif.dump(exif_dict)
                    self.picture.save(save_path, exif=exif_bytes)
                else:
                    self.picture.save(save_path)

            except ValueError:
                if self.has_exif:
                    exif_dict = piexif.load(self.picture.info["exif"])
                    exif_bytes = piexif.dump(exif_dict)
                    self.picture.save(save_path+".jpg",exif=exif_bytes)
                else:
                    self.picture.save(save_path + ".jpg")

            except Exception:
                tk.messagebox.showerror("Błąd zapisu", "Nastąpił błąd podczas zapisywania do pliku.")

    def chooseFile(self, event=None):
        """
        Metoda służąca do wybrania pliku obrazu w oknie dialogowym. Obraz następnie jest wyświetlany w przestrzeni roboczej.
        :param event: użycie skrótu klawiszowego przypisanego do metody
        :return:
        """
        try:
            if self.picture_path != None:
                reply = tkinter.messagebox.askyesno("Wybór nowego obrazu", "Masz otwarty plik. Czy chcesz go zapisać?")

                if reply:
                    self.saveFile()

                self.resetQueue()
                self.screen.destroy()

                file_path = tk.filedialog.askopenfilename()
                self.picture_path = file_path
                self.picture = Image.open(file_path)
                self.picture_starting_size = self.picture.size

                self.picture_copy = self.picture.copy()
                self.picture_TkImage = ImageTk.PhotoImage(self.picture)
                self.screen = tk.Label(self.workSpace, image=self.picture_TkImage)
                self.screen.pack()

                with open(self.picture_path, 'rb') as exif_file:
                    self.picture_EXIF = exif.Image(exif_file)
                    if (self.picture_EXIF.has_exif):
                        self.has_exif = True
                        self.exif_dict = self.picture_EXIF.get_all()
                    else:
                        self.has_exif = False

            else:
                file_path = tk.filedialog.askopenfilename()

                if file_path == "":
                    return

                self.picture_path = file_path
                self.picture = Image.open(file_path)
                self.picture_copy = self.picture.copy()
                self.picture_TkImage = ImageTk.PhotoImage(self.picture)
                self.screen = tk.Label(self.workSpace, image=self.picture_TkImage)
                self.screen.pack()

                self.picture_starting_size = self.picture.size
                self.proportions = self.picture_starting_size[0] / self.picture_starting_size[1]

                with open(self.picture_path, 'rb') as exif_file:
                    self.picture_EXIF = exif.Image(exif_file)
                    if (self.picture_EXIF.has_exif):
                        self.has_exif = True
                        self.exif_dict = self.picture_EXIF.get_all()
                    else:
                        self.has_exif = False
        except Exception:
            tk.messagebox.showerror("Błąd wyboru", "Podczas wczytywania pliku wystąpił błąd.\nSprawdź ponownie format pliku.")

    def resizeImage(self, event=None):
        """
        Metoda służąca do zmiany wielkości obrazu tak aby mieścił się w przestrzenii roboczej w odpowiednich proporcjach.
        :param event: zmiana wielkości okna aplikacji
        :return:
        """
        self.setStatusBar(f"Plik: {self.picture_path} ")

        try:
            new_height = self.workSpace.winfo_height()
            new_width = (int)(new_height* self.proportions)
        except TypeError:
            new_height = self.workSpace.winfo_height()
            new_width = self.workSpace.winfo_width()

        if self.picture != None and self.screen != None:

            #self.picture = self.picture_copy

            self.picture_TkImage = self.picture.resize((new_width, new_height), Image.ANTIALIAS)
            self.picture_TkImage = ImageTk.PhotoImage(self.picture_TkImage)

            try:
                self.screen.configure(image=self.picture_TkImage)
            except Exception:
                pass

    def __pictureIsNotNone(self):
        """
        Prywatna metoda używana do sprawdzenia czy aktualnie wybrany jest plik obrazu.
        W przeciwnym wypadku informuje użytkownika o braku obrazu, a przez to o niemożności wykonania akcji.
        :return: wartość logiczna dla obecnosci obrazu w aplikacji.
        """
        if self.picture == None:
            tk.messagebox.showerror("Brak obrazu", "Brak aktualnie wybranego obrazu.")
            return False
        else:
            return True

    #Funkcje ustawiania filtrów z PILLOW

    def blurFilter(self):
        """
        Metoda służąca do zastosowania filtra BLUR na aktualnie używanym obrazie.
        :return:
        """
        if self.__pictureIsNotNone():
            self.setStatusBar("Filtr blurowy")
            self.moves_list.append(self.picture)
            self.registerMove()
            self.picture = self.picture.filter(ImageFilter.BLUR)
            self.resizeImage()

    def contourfilter(self):
        """
        Metoda służąca do zastosowania filtra CONTOUR na aktualnie używanym obrazie.
        :return:
        """
        if self.__pictureIsNotNone():
            self.setStatusBar("Filtr kontury")
            self.moves_list.append(self.picture)
            self.registerMove()
            self.picture = self.picture.filter(ImageFilter.CONTOUR)
            self.resizeImage()

    def detailFilter(self):
        """
        Metoda służąca do zastosowania filtra DETAIL na aktualnie używanym obrazie.
        :return:
        """
        if self.__pictureIsNotNone():
            self.setStatusBar("Filtr detale")
            self.moves_list.append(self.picture)
            self.registerMove()
            self.picture = self.picture.filter(ImageFilter.DETAIL)
            self.resizeImage()

    def edgeEnchFilter(self):
        """
        Metoda służąca do zastosowania filtra EDGE_ENHACE na aktualnie używanym obrazie.
        :return:
        """
        if self.__pictureIsNotNone():
            self.setStatusBar("Filtr poprawienie krawedzi")
            self.moves_list.append(self.picture)
            self.registerMove()
            self.picture = self.picture.filter(ImageFilter.EDGE_ENHANCE)
            self.resizeImage()

    def embossFilter(self):
        """
        Metoda służąca do zastosowania filtra EMBOSS na aktualnie używanym obrazie.
        :return:
        """
        if self.__pictureIsNotNone():
            self.setStatusBar("Filtr EMBOSS")
            self.moves_list.append(self.picture)
            self.registerMove()
            self.picture = self.picture.filter(ImageFilter.EMBOSS)
            self.resizeImage()

    def findEdgesFilter(self):
        """
        Metoda służąca do zastosowania filtra FIND_EDGES na aktualnie używanym obrazie.
        :return:
        """
        if self.__pictureIsNotNone():
            self.setStatusBar("Filtr krawędzie")
            self.moves_list.append(self.picture)
            self.registerMove()
            self.picture = self.picture.filter(ImageFilter.FIND_EDGES)
            self.resizeImage()

    def edgeEnchMFilter(self):
        """
        Metoda służąca do zastosowania filtra EDGE_ENHANCE_MORE na aktualnie używanym obrazie.
        :return:
        """
        if self.__pictureIsNotNone():
            self.setStatusBar("Filtr większego poprawienia krawędzi")
            self.moves_list.append(self.picture)
            self.registerMove()
            self.picture = self.picture.filter(ImageFilter.EDGE_ENHANCE_MORE)
            self.resizeImage()

    def sharpenFilter(self):
        """
        Metoda służąca do zastosowania filtra SHARPEN na aktualnie używanym obrazie.
        :return:
        """
        if self.__pictureIsNotNone():
            self.setStatusBar("Filtr wyostrzanie")
            self.moves_list.append(self.picture)
            self.registerMove()
            self.picture = self.picture.filter(ImageFilter.SHARPEN)
            self.resizeImage()

    def smoothFilter(self):
        """
        Metoda służąca do zastosowania filtra SMOOTH na aktualnie używanym obrazie.
        :return:
        """
        if self.__pictureIsNotNone():
            self.setStatusBar("Filtr wygładzanie")
            self.moves_list.append(self.picture)
            self.registerMove()
            self.picture = self.picture.filter(ImageFilter.SMOOTH)
            self.resizeImage()

    def smoothMFilter(self):
        """
        Metoda służąca do zastosowania filtra SMOOTH_MORE na aktualnie używanym obrazie.
        :return:
        """
        if self.__pictureIsNotNone():
            self.setStatusBar("Filtr lepsze wygładzanie")
            self.moves_list.append(self.picture)
            self.registerMove()
            self.picture = self.picture.filter(ImageFilter.SMOOTH_MORE)
            self.resizeImage()

    def hexagonFrameFilter(self):
        """
        Metoda służąca do zastosowania filtra nakładającego ramkę, pozostawiającego środek w kształcie
        6-kąta, na aktualnie używanym obrazie.
        :return:
        """
        if self.__pictureIsNotNone():
            for i in range(8):
               self.__rotateToRightDeg(45)

    def grayscale(self):
        """
        Metoda służąca do zastosowania filtra GREYSCALE na aktualnie używanym obrazie.
        :return:
        """
        if self.__pictureIsNotNone():
            self.setStatusBar("Przekształcam do szarości")
            self.moves_list.append(self.picture)
            self.registerMove()
            self.picture = pil.ImageOps.grayscale(self.picture)
            self.resizeImage()

    #Funkcje obracające zdjęcie

    def RotateToLeft(self):
        """
        Metoda służąca do obrócenia obrazu o 90 stopni w lewo
        :return:
        """
        if self.__pictureIsNotNone():
            self.setStatusBar("Obracam w prawo")
            self.moves_list.append(self.picture)
            self.registerMove()
            self.picture = self.picture.transpose(pil.Image.ROTATE_90)
            self.resizeImage()

    def RotateToRight(self):
        """
        Metoda służąca do obrócenia obrazu o 90 stopni w prawo
        :return:
        """
        if self.__pictureIsNotNone():
            self.setStatusBar("Obracam w lewo")
            self.moves_list.append(self.picture)
            self.registerMove()
            self.picture = self.picture.transpose(pil.Image.ROTATE_270)
            self.resizeImage()

    def rotateToRightDeg(self):
        """
        Metoda służąca do obrócenia obrazu w prawo o wybrany przez użytkownika w oknie dialogowym kąt.
        :return:
        """
        if self.__pictureIsNotNone():

            def getDeg():
                self.__rotateToRightDeg(right_slider.get())
                right_root.destroy()

            right_root = tk.Toplevel()
            right_root.geometry("300x150")
            right_root.title("Obracanie w lewo")
            right_root.minsize(400, 150)
            right_root.maxsize(400, 150)
            right_info = tk.Label(right_root, text="Wybierz kąt obrotu w prawo")
            right_info.pack()
            right_slider = tk.Scale(right_root,length=400, from_=0, to=360, orient=tk.HORIZONTAL, tickinterval=20)
            right_slider.set(0)
            right_slider.pack()
            button = tk.Button(right_root, text="Obróć", command = lambda: getDeg())
            button.pack()

    def __rotateToRightDeg(self, deg=45):
        """
        Prywatna metoda służąca do obrócenia obrazu o podany kąt.
        :param deg: kąt o który zostanie obrócony w prawo obraz, wartość z zakresu od 0 do 360
        :return:
        """
        if self.__pictureIsNotNone():
            self.setStatusBar(f"Obracam w prawo o {deg} stopni")
            self.moves_list.append(self.picture)
            self.registerMove()
            self.picture = self.picture.rotate(deg)
            self.resizeImage()

    def rotateToLeftDeg(self):
        """
        Metoda służąca do obrócenia obrazu w lewo o wybrany przez użytkownika w oknie 	dialogowym kąt.
        :return:
        """
        if self.__pictureIsNotNone():

            def getDeg():
                self.__rotateToLeftDeg(left_slider.get())
                left_root.destroy()

            left_root = tk.Toplevel()
            left_root.geometry("300x150")
            left_root.title("Obracanie w lewo")
            left_root.minsize(400, 150)
            left_root.maxsize(400, 150)
            left_info = tk.Label(left_root, text="Wybierz kąt obrotu w lewo")
            left_info.pack()
            left_slider = tk.Scale(left_root,length=400, from_=0, to=360, orient=tk.HORIZONTAL, tickinterval=20)
            left_slider.set(0)
            left_slider.pack()
            button = tk.Button(left_root, text="Obróć", command = lambda: getDeg())
            button.pack()

    def __rotateToLeftDeg(self, deg=45):
        """
        Prywatna metoda służąca do obrócenia obrazu o podany kąt.
        :param deg: kąt o który zostanie obrócony w lewo obraz, wartość z zakresu od 0 do 360
        :return:
        """
        if self.__pictureIsNotNone():
            self.setStatusBar(f"Obracam w lewo o {deg} stopni")
            self.moves_list.append(self.picture)
            self.registerMove()
            self.picture = self.picture.rotate(-deg)
            self.resizeImage()

    def flipLeftRigth(self):
        """
        Metoda obracająca obraz w poziomie wokół własnej osi.
        :return:
        """
        if self.__pictureIsNotNone():
            self.setStatusBar("Odwracam w poziomie")
            self.moves_list.append(self.picture)
            self.registerMove()
            self.picture = self.picture.transpose(pil.Image.FLIP_LEFT_RIGHT)
            self.resizeImage()

    def flipTopBottom(self):
        """
        Metoda obracająca obraz w pionie wokół własnej osi.
        :return:
        """
        if self.__pictureIsNotNone():
            self.setStatusBar("Odwracam w pionie")
            self.moves_list.append(self.picture)
            self.registerMove()
            self.picture = self.picture.transpose(pil.Image.FLIP_TOP_BOTTOM)
            self.resizeImage()

    #Funkcje zmiany kroku

    def goBack(self, event=None):
        """
        Metoda służąca do cofania się do poprzedniego kroku modyfikcji obrazu.
        :param event: użycie skrótu klawiszowego przypisanego do metody
        :return:
        """
        if self.current_move > 0:
            self.setStatusBar("cofam")
            self.current_move -= 1
            self.picture = self.moves_list[self.current_move]
        self.resizeImage()

    def goForward(self, event=None):
        """
        Metoda służąca do powrócenia do następnego kroku jeśli wcześniej zostało wykonane cofnięcie.
        :param event: użycie skrótu klawiszowego przypisany do metody
        :return:
        """
        if self.current_move < (len(self.moves_list) - 1):
            self.setStatusBar("następny krok")
            self.current_move += 1
            self.picture = self.moves_list[self.current_move]
        self.resizeImage()

    def resetQueue(self):
        """
        Metoda służąca do zresetowania historii modyfikacji
        :return:
        """
        self.moves_list = []
        self.current_move = 0

    def registerMove(self):
        """
        Metoda służąca do zarejestrowania wykonania czynności modyfikującej obraz.
        :return:
        """
        self.current_move += 1

        if self.current_move < len(self.moves_list) - 1:
            new_queue = []
            for i in range(self.current_move):
                new_queue.append(self.moves_list[i])
            self.moves_list = new_queue
            self.current_move = len(self.moves_list)

    #Funkce edycji obrazu
    def blendWithImage(self):
        """
        Metoda służąca do połączenia aktualnie używanego obrazu z obrazem wybranym przez użytkownika w oknie dialogowym.
        :return:
        """
        if self.__pictureIsNotNone():
            second_file = tk.filedialog.askopenfilename()
            try:
                second_picture = Image.open(second_file)
            except Exception:
                tk.messagebox.showerror("Błąd łączenia", "Nastąpił błąd podczas wybierania pliku do złączenia, sprawdź format pliku")
                return

            second_picture = second_picture.resize(self.picture.size)

            def __getAlphaVar():
                self.__blend(second_picture, alpha_slider.get())
                blend_root.destroy()

            blend_root = tk.Toplevel()
            blend_root.title("Ustawianie parametru alfa")
            blend_root.geometry("300x175")
            blend_root.minsize(300, 175)
            blend_root.maxsize(300, 175)
            blend_info = tk.Label(blend_root, text="Wybierz parametr alfa.\n(100-obraz drugi)\n(0-obraz pierwszy)")
            blend_info.pack()
            alpha_slider = tk.Scale(blend_root, length= 300, from_=0, to=100, orient=tk.HORIZONTAL, tickinterval=10)
            alpha_slider.set(50)
            alpha_slider.pack()
            button = tk.Button(blend_root, text="Ustaw parametr alfa.", command=__getAlphaVar)
            button.pack()

    def __blend(self, second_picture, alpha):
        """
        Prywatna metoda łącząca 2 obrazy
        :param second_picture: 2 obraz, który zostanie połączony z pierwszym
        :param alpha: parametr alfa określający stopień złączenia obrazu.
        Przyjmuje wartości rzeczywiste z przedziału od 0 do 1 gdzie 0 oznacza, że wynikowy
        obraz będzie identyczny jak pierwszy, a 1 że będzie identyczny jak drugi.
        :return:
        """
        self.setStatusBar(f"łączę z {second_picture}")
        self.moves_list.append(self.picture)
        self.registerMove()
        self.picture = pil.Image.blend(self.picture, second_picture, alpha/100)
        self.resizeImage()

    def diffrence(self):
        """
        Metoda służąca do zmienienia obrazu na obraz otrzymany jako wynik różnicy pomiędzy odpowiednimi pikselami.
        :return:
        """
        if self.__pictureIsNotNone():
            second_file = tk.filedialog.askopenfilename()
            try:
                second_picture = Image.open(second_file)
            except Exception:
                tk.messagebox.showerror("Błąd łączenia",
                                        "Nastąpił błąd podczas wybierania pliku do złączenia, sprawdź format pliku")
                return

            second_picture = second_picture.resize(self.picture.size)

            self.setStatusBar(f"łączę z {second_picture}")
            self.moves_list.append(self.picture)
            self.registerMove()
            self.picture = pil.ImageChops.difference(self.picture, second_picture)
            self.resizeImage()

    def invertImage(self):
        """
        Metoda służąca do odwracania kolorów na aktualnie używanym obrazie.
        :return:
        """
        if self.__pictureIsNotNone():
            self.setStatusBar(f"Odwracam obraz")
            self.moves_list.append(self.picture)
            self.registerMove()
            self.picture = pil.ImageChops.invert(self.picture)
            self.resizeImage()

    def scaleImage(self):
        """
        Metoda służąca do przeskalowania rozmiaru obrazu o współczynnik podany przez użytkownika w oknie dialogowym.
        :return:
        """
        if self.__pictureIsNotNone():
            def getScale():
                self.__scaleImage(scale_slider.get() / 10)
                scale_root.destroy()

            scale_root = tk.Toplevel()
            scale_root.title("Ustawianie skali")
            scale_root.geometry("300x150")
            scale_root.minsize(300, 150)
            scale_root.maxsize(300, 150)
            scale_info = tk.Label(scale_root, text="Zmiana skali obrazu.\n(10 oznacza brak zmian)")
            scale_info.pack()
            scale_slider = tk.Scale(scale_root, length=300, from_=0, to=50, orient=tk.HORIZONTAL, tickinterval=5)
            scale_slider.set(10)
            scale_slider.pack()
            button = tk.Button(scale_root, text="Ustaw skalę.", command= lambda: getScale())
            button.pack()

    def __scaleImage(self, scale):
        """
        Prywatna metoda skalująca wielkość obrazu
        :param scale: parametr o jaki przeskalowana zostanie wielkość obrazu.
        :return:
        """
        try:
            self.setStatusBar(f"Skaluje obraz")
            self.moves_list.append(self.picture)
            self.registerMove()
            self.picture = pil.ImageOps.scale(self.picture, scale)
            self.resizeImage()
        except MemoryError:
            tk.messagebox.showerror("Bląd skalowania", "Nie można bardziej skalować tego obrazu.")

    def posterizeImage(self):
        """
        Metoda służąca do posteryzacji aktualnie używanego obrazu poprzez redukcję liczby bitów dla każdego kanału koloru.
        Liczba bitów podawana jest przez użytkownika w oknie dialogowym.
        :return:
        """
        if self.__pictureIsNotNone():
            def getPosterizationBits():
                self.__posterize(posterization_slider.get())
                posterization_root.destroy()

            posterization_root = tk.Toplevel()
            posterization_root.title("Wybór liczby bitów posteryzacji")
            posterization_root.geometry("300x150")
            posterization_root.minsize(300, 150)
            posterization_root.maxsize(300, 150)
            posterization_info = tk.Label(posterization_root, text="Wybór liczby bitów do posteryzacji.\n(8 oznacza brak zmian)")
            posterization_info.pack()
            posterization_slider = tk.Scale(posterization_root, length=100, from_=1, to=8, orient=tk.HORIZONTAL, tickinterval=1)
            posterization_slider.set(8)
            posterization_slider.pack()
            button = tk.Button(posterization_root, text="Ustaw posteryzacje.", command= lambda: getPosterizationBits())
            button.pack()

    def __posterize(self, bits):
        """
        Prywatna metoda służąca do posteryzacji.
        :param bits: Liczba bitów do zostawienia na każdym kanale.
        :return:
        """
        self.setStatusBar("Posteryzuję obraz")
        self.moves_list.append(self.picture)
        self.registerMove()
        self.picture = pil.ImageOps.posterize(self.picture, bits)
        self.resizeImage()

    def changeBrightness(self, event=None):
        """
        Metoda służąca do zmiany jasności aktualnie używanego obrazu o współczynnik podany przez użytkownika w oknie dialogowym.
        :param event: użycie skrótu klawiszowego przypisany do metody
        :return:
        """
        if self.__pictureIsNotNone():
            def getBrightFactor():
                self.__changeBrightness(brightness_slider.get() / 10)
                brightness_root.destroy()


            brightness_root = tk.Toplevel()
            brightness_root.title("Skala jasności")
            brightness_root.geometry("300x150")
            brightness_root.minsize(300, 150)
            brightness_root.maxsize(300, 150)
            brightness_info = tk.Label(brightness_root, text="Skala jasności.\n(10 oznacza brak zmian)")
            brightness_info.pack()
            brightness_slider = tk.Scale(brightness_root, length=200, from_=0, to=20, orient=tk.HORIZONTAL, tickinterval=2)
            brightness_slider.set(10)
            brightness_slider.pack()
            button = tk.Button(brightness_root, text="Ustaw jasność.", command=lambda: getBrightFactor())
            button.pack()

    def __changeBrightness(self, factor):
        """
        Prywatna metoda służąca do zmiany jasności o dany współczynnik.
        :param factor: współczynnik zmiany jasności
        :return:
        """
        enchancer = ImageEnhance.Brightness(self.picture)
        self.setStatusBar("Zmieniam jasność")
        self.moves_list.append(self.picture)
        self.registerMove()
        self.picture = enchancer.enhance(factor)
        self.resizeImage()

    def changeSharpness(self, event=None):
        """
        Metoda służąca do wyostrzania aktualnie używanego obrazu o współczynnik podany przez użytkownika w oknie dialogowym.
        :param event: użycie skrótu klawiszowego przypisany do metody
        :return:
        """
        if self.__pictureIsNotNone():
            def getSharpFactor():
                self.__changeSharpness(sharpness_slider.get() / 10)
                sharpness_root.destroy()

            sharpness_root = tk.Toplevel()
            sharpness_root.title("Skala ostrości")
            sharpness_root.geometry("300x150")
            sharpness_root.minsize(300, 150)
            sharpness_root.maxsize(300, 150)
            sharpness_info = tk.Label(sharpness_root, text="Skala ostrości.\n(10 oznacza brak zmian)")
            sharpness_info.pack()
            sharpness_slider = tk.Scale(sharpness_root, length=200, from_=0, to=20, orient=tk.HORIZONTAL, tickinterval=2)
            sharpness_slider.set(10)
            sharpness_slider.pack()
            button = tk.Button(sharpness_root, text="Ustaw ostrość.", command=lambda: getSharpFactor())
            button.pack()

    def __changeSharpness(self, factor):
        """
        Prywatna metoda służąca do wyostrzenia obrazu o podany współczynnik
        :param factor: współczynnik ostrości
        :return:
        """
        enchancer = ImageEnhance.Sharpness(self.picture)
        self.setStatusBar("Zmieniam ostrość")
        self.moves_list.append(self.picture)
        self.registerMove()
        self.picture = enchancer.enhance(factor)
        self.resizeImage()

    def changeContrast(self, event=None):
        """
        Metoda służąca do zmiany kontrastu o współczynnik podany przez użytkownika w oknie dialogowym.
        :param event: użycie skrótu klawiszowego przypisany do metody
        :return:
        """
        if self.__pictureIsNotNone():
            def getContrFactor():
                self.__changeContrast(contrast_slider.get() / 100)
                contrast_root.destroy()


            contrast_root = tk.Toplevel()
            contrast_root.title("Skala ostrości")
            contrast_root.geometry("450x150")
            contrast_root.minsize(450, 150)
            contrast_root.maxsize(450, 150)
            contrast_info = tk.Label(contrast_root,text="Skala kontrastu.\n(Wartość 100 oznacza brak zmiany)")
            contrast_info.pack()
            contrast_slider = tk.Scale(contrast_root, length=430, from_=0, to=200, orient=tk.HORIZONTAL, tickinterval=10)
            contrast_slider.set(100)
            contrast_slider.pack()
            button = tk.Button(contrast_root, text="Ustaw kontrast.", command=lambda: getContrFactor())
            button.pack()

    def __changeContrast(self, factor):
        """
        Prywatna metoda służąca do zmiany kontrastu na aktualnym obrazie.
        :param factor: współczynnik o który zostanie zmieniony kontrast
        :return:
        """
        enchancer = ImageEnhance.Contrast(self.picture)
        self.setStatusBar("Zmieniam kontrast")
        self.moves_list.append(self.picture)
        self.registerMove()
        self.picture = enchancer.enhance(factor)
        self.resizeImage()

    def changeColourSat(self, event=None):
        """
        Metoda służąca do zmienienia nasycenia kolorów na aktualnie używanym obrazie o współczynnik
        podany przez użytkownika w oknie dialogowym.
        :param event: użycie skrótu klawiszowego przypisany do metody
        :return:
        """
        if self.__pictureIsNotNone():
            def getColourFactor():
                self.__changeColourSat(contrast_slider.get() / 10)
                colour_root.destroy()


            colour_root = tk.Toplevel()
            colour_root.title("Skala nasycenia kolorów")
            colour_root.geometry("300x150")
            colour_root.maxsize(300,150)
            colour_root.minsize(300,150)
            colour_info = tk.Label(colour_root, text="Skala nasycenia kolorów.\n (Wartość 10 oznacza brak zmiany)")
            colour_info.pack()
            contrast_slider = tk.Scale(colour_root, length=300, from_=0, to=50, orient=tk.HORIZONTAL, tickinterval=10)
            contrast_slider.set(10)
            contrast_slider.pack()
            button = tk.Button(colour_root, text="Ustaw kolor.", command=lambda: getColourFactor())
            button.pack()

    def __changeColourSat(self, factor):
        """
        Prywatna metoda służaca do zmiany nasycenia kolorów na aktualnym obrazie.
        :param factor: współczynnik o który zostanie zmienione nasycenie kolorów
        :return:
        """
        enchancer = ImageEnhance.Color(self.picture)
        self.setStatusBar("Zmieniam nasycenie kolorów")
        self.moves_list.append(self.picture)
        self.registerMove()
        self.picture = enchancer.enhance(factor)
        self.resizeImage()

    #Funkcje obslugujące EXIF

    def saveEXIF(self, event=None):
        """
        Metoda służąca do zapisu danych exif do danego obrazu. Zapisuje dokładnie na ten sam plik zmodyfikowane metadane.
        Użycie nie zapisuje modyfikacji wykonanym na samym obrazie. Modyfikacje obrazu trzeba zapisywać
        osobno, najlepiej poprzez opcje zapisz jako, aby uniknąć nadpisania metadanych exif przez dane początkowe.
        :param event: użycie skrótu klawiszowego przypisany do metody
        :return:
        """
        if self.__pictureIsNotNone():
            self.setStatusBar("Zapisuję dane EXIF")
            with open(self.picture_path, 'wb') as new_image:
                new_image.write(self.picture_EXIF.get_file())

            tk.messagebox.showinfo("Zapis EXIF", "Uwaga dane exif zostaną zapisane razem z podstawowym obrazem w jego lokalizacji. Jeśli chcesz zapisać zmiany graficzne musisz zrobić to osobno.")

    def deleteEXIF(self, event=None):
        """
        Metoda służąca do usunięcia wszystkich metadanych exif na obrazie
        :param event: użycie skrótu klawiszowego przypisany do metody
        :return:
        """
        if self.__pictureIsNotNone():
            self.setStatusBar("Usuwam dane EXIF")
            self.picture_EXIF.delete_all()
            self.has_exif = False

    def showExif(self, event=None):
        """
        Metoda służąca do wyświetlenia okna  pozwalającego na  przeglądaie danych exif.
        :param event: użycie skrótu klawiszowego przypisany do metody
        :return:
        """
        if self.__pictureIsNotNone():
            if self.has_exif is False:
                tk.messagebox.showerror("Brak Exif", "Modyfikowany obraz nie ma metadanych EXIF.")
                return
            self.setStatusBar("Przeglądanie danych EXIF")

            exif_version = self.picture_EXIF.get("exif_version")

            def closeShowExif():
                self.resizeImage()
                exif_root.destroy()

            exif_root = tk.Toplevel()
            exif_root.title(f"Metadane EXIF wersja {exif_version}")
            exif_root.geometry("430x300")
            exif_root.maxsize(430, 300)
            exif_root.minsize(430, 300)

            exif_phone = tk.Frame(exif_root)
            phone_make = tk.Label(exif_phone, text="Marka telefonu: "+self.picture_EXIF.get("make", default="Brak"), width=30)
            phone_make.grid(row = 2, columnspan=2, sticky=tk.W)
            phone_model = tk.Label(exif_phone, text="Model telefonu: "+self.picture_EXIF.get("model",default="Brak"), width=30)
            phone_model.grid(row= 2, column=8, columnspan=2, sticky=tk.W)
            separator = tk.Label(exif_phone, text="--------------------------------------------------------------------------------------")
            separator.grid(row=4, column=0, columnspan=15)
            exif_phone.pack(fill=tk.X)

            exif_datetime = tk.Frame(exif_root)
            date_original = tk.Label(exif_datetime, text="Czas wykonania zdjecia: "+self.picture_EXIF.get("datetime_original", default= "Nieznany"))
            date_original.grid(row = 2, columnspan=2, sticky=tk.W)
            date_mod = tk.Label(exif_datetime, text="Czas modyfikacji zdjęcia: "+self.picture_EXIF.get("datetime", default= "Nieznany"))
            date_mod.grid(row= 4, column=0, columnspan=2, sticky=tk.W)
            separator = tk.Label(exif_datetime,text="--------------------------------------------------------------------------------------")
            separator.grid(row=6, column=0, columnspan=15)
            exif_datetime.pack(fill=tk.X)


            if "gps_latitude" in self.exif_dict:
                exif_localization = tk.Frame(exif_root)
                localization = tk.Label(exif_localization, text="Koordynaty wykonania zdjecia: ")
                localization.grid(row=2, columnspan=2, sticky=tk.W)
                latitude = tk.Label(exif_localization, text=f"{self.__dmsCordinatesToDDCordinates(self.picture_EXIF.gps_latitude, self.picture_EXIF.gps_latitude_ref)} {self.picture_EXIF.gps_latitude_ref}")
                latitude.grid(row=2, column=8 ,columnspan=2, sticky=tk.W)
                longitude = tk.Label(exif_localization, text=f"{self.__dmsCordinatesToDDCordinates(self.picture_EXIF.gps_longitude, self.picture_EXIF.gps_longitude_ref)} {self.picture_EXIF.gps_longitude_ref}")
                longitude.grid(row=2, column= 12, columnspan=2, sticky=tk.W)
                exif_localization.pack(fill=tk.X)
            else:
                exif_localization = tk.Frame(exif_root)
                localization = tk.Label(exif_localization, text="Koordynaty wykonania zdjecia: Nieznane")
                localization.pack()
                exif_localization.pack(fill=tk.X)


            exif_other = tk.Frame(exif_root)
            separator = tk.Label(exif_other, text="--------------------------------------------------------------------------------------")
            separator.grid(row=0, column=0, columnspan=15, sticky=tk.W)
            other_info = tk.Label(exif_other, text="Wpisz tag exif do którego chcesz uzyskać dostęp:")
            other_info.grid(row=1, column=0, columnspan=4, sticky=tk.W)

            def getTag():
                if tag_name.get() in self.exif_dict:
                    tag_result.configure(text=f"{tag_name.get()}: {self.picture_EXIF.get(tag_name.get())}")
                else:
                    tag_result.configure(text=f"Brak tagu {tag_name.get()} wśród metadanych")


            tag_name = tk.StringVar()
            tag_entry = tk.Entry(exif_other, textvariable=tag_name)
            tag_button = tk.Button(exif_other, text="Wyszukaj", command=getTag)
            tag_entry.grid(row=2, column=0, columnspan=4, sticky=tk.W)
            tag_button.grid(row=2, column=4, columnspan=4)
            tag_result = tk.Label(exif_other, text="...........")
            tag_result.grid(row=3, column=0, columnspan=8, sticky=tk.W)


            exif_other.pack(fill=tk.X)


            exitButton = tk.Button(exif_root, command=closeShowExif, text="Wyjdź")
            exitButton.pack()

    def changeExif(self, event=None):
        """
        Metoda służąca do wyświetlenia okna służącego do modyfikacji metadanych exif.
        :param event: użycie skrótu klawiszowego przypisany do metody
        :return:
        """
        if self.__pictureIsNotNone():
            if self.has_exif is False:
                tk.messagebox.showerror("Brak Exif", "Modyfikowany obraz nie ma metadanych EXIF.")
                return
            self.setStatusBar("Modyfikowanie danych EXIF")

            def closeModExif():
                self.resizeImage()
                exif_mod_root.destroy()

            exif_mod_root = tk.Toplevel()
            exif_mod_root.title(f"Metadane EXIF modyfikacja")
            exif_mod_root.geometry("430x300")
            exif_mod_root.maxsize(430, 300)
            exif_mod_root.minsize(430, 300)

            def getTag():
                if search_name.get() in self.exif_dict:
                    search_result.configure(text=f"{search_name.get()}: {self.picture_EXIF.get(search_name.get())}")
                else:
                    search_result.configure(text=f"Brak tagu {search_name.get()} wśród metadanych")

            search_root = tk.Frame(exif_mod_root)
            search_title = tk.Label(search_root, text="Wyszukiwanie metadanych po tagu")
            search_title.grid(row=0, column=0, columnspan=4, sticky=tk.W)
            search_name = tk.StringVar()
            search_entry = tk.Entry(search_root, textvariable=search_name)
            search_entry.grid(row=2, column=0, columnspan=4, sticky=tk.W)
            search_result = tk.Label(search_root, text="...........")
            search_result.grid(row=4, column=0, columnspan=4, sticky=tk.W)
            search_button = tk.Button(search_root, text="Wyszukaj", command=getTag)
            search_button.grid(row=2, column=5, columnspan=4, sticky=tk.W)
            separator = tk.Label(search_root,text="--------------------------------------------------------------------------------------")
            separator.grid(row=6, column=0, columnspan=15, sticky=tk.W)
            search_root.pack(fill=tk.X)


            def modTag():
                print(mod_tag_entry.get(), mod_value_entry.get())
                self.picture_EXIF.set(mod_tag_entry.get(), mod_value_entry.get())
                self.exif_dict = self.picture_EXIF.get_all()

            modification_root = tk.Frame(exif_mod_root)
            mod_title = tk.Label(modification_root, text="\t\t\tModyfikacja metadanych")
            mod_title.grid(row=0, columnspan=4)

            mod_tag_title = tk.Label(modification_root, text="Wpisz tag:")
            mod_tag_title.grid(row=2, column=0, columnspan=6, sticky=tk.W)

            mod_tag_name = tk.StringVar()
            mod_tag_entry = tk.Entry(modification_root, textvariable=mod_tag_name)
            mod_tag_entry.grid(row=4, column=0, columnspan=4, sticky=tk.W)

            mod_value_title = tk.Label(modification_root, text="Wpisz wartość:")
            mod_value_title.grid(row=2, column=6, columnspan=4, sticky=tk.E)

            mod_value_name = tk.StringVar()
            mod_value_entry = tk.Entry(modification_root, textvariable=mod_value_name)
            mod_value_entry.grid(row=4, column=6, columnspan=4, sticky=tk.E)

            mod_button = tk.Button(modification_root, text="Zmień EXIF", command=modTag)
            mod_button.grid(row=6, column=2, columnspan=2, sticky=tk.S)

            modification_root.pack(fill=tk.X)



            exitButton = tk.Button(exif_mod_root, command=closeModExif, text="Wyjdź")
            exitButton.pack()

    def showPhotoLocation(self, event=None):
        """
        Metoda służąca do wyświetlenia w przeglądarce lokalizacji wykonania zdjęcia jeśli są one obecne w metadanych exif.
        :param event: użycie skrótu klawiszowego przypisany do metody
        :return:
        """
        if self.__pictureIsNotNone():
            if self.has_exif is False:
                tk.messagebox.showerror("Brak danych","Nie można wyświetlić lokalizacji")
                return
            elif "gps_latitude" not in self.exif_dict:
                tk.messagebox.showerror("Brak danych lokalizacji", "Nie można wyświetlić lokalizacji")
                return
            else:
                self.__drawMap()

    def __dmsCordinatesToDDCordinates(self, coordinates, coordinates_ref):
        """
        prywatna metoda służąca do zmiany koordynatów otrzymanych z danych exif na kordynaty
        w postaci odczytywalnej przez człowieka i mapy google.
        :param coordinates: koordynaty w postaci krotki (stopnie, minuty, sekundy)
        :param coordinates_ref: Znak informujący o półkuli współrzędnych.
        :return:
        """
        decimal_degrees = coordinates[0] + \
                          coordinates[1] / 60 + \
                          coordinates[2] / 3600

        if coordinates_ref == "S" or coordinates_ref == "W":
            decimal_degrees = -decimal_degrees

        return decimal_degrees

    def __drawMap(self):
        """
        Prywatna metoda służąca do otwarcia w przeglądarce okna map google z zaznaczoną
        lokazizacją wykonania aktualnego zdjęcia odczytaną z metadanych exif.
        :return:
        """
        import webbrowser

        decimal_latitude = self.__dmsCordinatesToDDCordinates(self.picture_EXIF.gps_latitude, self.picture_EXIF.gps_latitude_ref)
        decimal_longitude = self.__dmsCordinatesToDDCordinates(self.picture_EXIF.gps_longitude, self.picture_EXIF.gps_longitude_ref)
        url = f"https://www.google.com/maps?q={decimal_latitude},{decimal_longitude}"
        webbrowser.open_new_tab(url)



if __name__ == '__main__':
    root = tk.Tk()
    app = Gui(master=root)
    app.mainloop()
    pass