from contextlib import nullcontext
from curses.ascii import NUL
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
import os

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
		destination_path=""
		with wx.DirDialog(self, "Select folder to create evaluation in:",
                       style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT) as dirDialog:

			if dirDialog.ShowModal() == wx.ID_CANCEL:
				return

			destination_path = os.path.join(dirDialog.GetPath(),'evaluation') 

			if self.SolDBTabs.GetSelection() == 0:
				#single deck
				args = Namespace(username=self.userCtrl.Value, 
						type=self.calcType(),
						id=self.idCtrl.Value,
						filename=None,
						eval=destination_path,
						graph=self.createGraphCtrl.Value,
						filter=None,
						offline=False,
						select_pairs=False
						)
			else:
				if self.filterCtrl.Value != "":
					filterContent = self.filterCtrl.Value
				else:
					filterContent = None

				args = Namespace(username=self.userCtrl.Value, 
						type=self.calcType(),
						id=self.idCtrl.Value,
						filename=None,
						eval=destination_path,
						graph=self.createGraphCtrl.Value,
						filter=filterContent,
						offline=self.offlineCtrl.Value,
						select_pairs=self.selectPairsCtrl.Value
						)

		SolDB(args)

	

if __name__ == '__main__':
	app = wx.App(redirect=False)
	frame = SolDBMain(None)
	frame.Show(True)
	app.MainLoop()


#issues
#- doesn't handle blank cache file
#- expects txt folder to exist, output not optional