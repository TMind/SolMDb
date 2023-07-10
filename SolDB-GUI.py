from DeckLibrary import DeckLibrary
from Card_Library import Deck, UniversalCardLibrary
from NetApi import NetApi
import Evaluation as ev
from CacheManager import CacheManager


import wx
from wx.adv import AboutBox, AboutDialogInfo
from wxSolDB import SolDBMainFrame, SolDBPanel

from urllib.parse import urlparse
from soldb import main as SolDB
from argparse import Namespace

class SolDBMain(SolDBMainFrame):
	def __init__(self, parent):
		super().__init__(parent)
		self.panel = SolDBWindow(self)
		self.Show()
		self.Bind(wx.EVT_CLOSE, self.OnClose)
		
	def OnClose(self, event):
		#elf.panel.saveDefaults()
		event.Skip()
	
	def onQuit(self, event):
		self.Close()

	def showAbout(self, event):
		aboutInfo = AboutDialogInfo()
		aboutInfo.SetName("SolDB")
		aboutInfo.SetVersion("0.1")
		aboutInfo.SetDescription("")
		aboutInfo.SetCopyright("(C) tmind")
		aboutInfo.SetWebSite("")
		#aboutInfo.AddDeveloper("Gorman Christian with thanks to (and no affiliation):")
		aboutInfo.AddDeveloper("reportlab https://www.reportlab.com/opensource/")
		aboutInfo.AddDeveloper("requests https://requests.readthedocs.io/en/latest/")
		aboutInfo.AddDeveloper("wxWidgets https://wxwidgets.org/about/licence/")
		aboutInfo.AddDeveloper("wxPython https://wxpython.org/")	
		aboutInfo.AddDeveloper("appdirs  https://github.com/ActiveState/appdirs")
		aboutInfo.AddDeveloper("Stoneblade https://www.stoneblade.com")
		aboutInfo.AddArtist("Symbols/Artwork/SFF Logo https://www.stoneblade.com")
		#aboutInfo.SetIcon(self.panel.icon)

		AboutBox(aboutInfo)
class SolDBWindow(SolDBPanel):

	def calcType(self):
		if self.deckTypeCtrl.GetSelection() == "Fused Deck":
			return "fuseddeck"
		else:
			return "deck"

	def analyzeDeck( self, event ):
		with wx.FileDialog(self, "Save evalulation files as:",
                       style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT) as fileDialog:

			if fileDialog.ShowModal() == wx.ID_CANCEL:
				return

			saveAsPath = fileDialog.GetPath()


		args = Namespace(username=self.userCtrl.Value, 
						type=self.calcType(),
						id=self.idCtrl.Value,
						filename=None,
						eval=saveAsPath,
						graph=False,
						filter=None,
						select_pairs=False
						)

		SolDB(args)

	def evalDecks( self, event ):
		event.Skip()

	

if __name__ == '__main__':
	app = wx.App(redirect=False)
	frame = SolDBMain(None)
	frame.Show(True)
	app.MainLoop()


#issues
#- doesn't handle blank cache file
#- expects txt folder to exist, output not optional