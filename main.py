import matplotlib
matplotlib.use("TkAgg")

from src.app import App

if __name__ == "__main__":
    app = App()
    app.mainloop()
