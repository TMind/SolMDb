# -*- coding: utf-8 -*-

###########################################################################
## Python code generated with wxFormBuilder (version 3.10.1-0-g8feb16b)
## http://www.wxformbuilder.org/
##
## PLEASE DO *NOT* EDIT THIS FILE!
###########################################################################

import wx
import wx.xrc

###########################################################################
## Class SolDBMainFrame
###########################################################################

class SolDBMainFrame ( wx.Frame ):

	def __init__( self, parent ):
		wx.Frame.__init__ ( self, parent, id = wx.ID_ANY, title = u"SolDB", pos = wx.DefaultPosition, size = wx.Size( 500,300 ), style = wx.DEFAULT_FRAME_STYLE|wx.TAB_TRAVERSAL )

		self.SetSizeHints( wx.DefaultSize, wx.DefaultSize )

		self.SolDBMenuBar = wx.MenuBar( 0 )
		self.SolDBMenu = wx.Menu()
		self.aboutItem = wx.MenuItem( self.SolDBMenu, wx.ID_ABOUT, u"About", wx.EmptyString, wx.ITEM_NORMAL )
		self.SolDBMenu.Append( self.aboutItem )

		self.SolDBMenu.AppendSeparator()

		self.quiteItem = wx.MenuItem( self.SolDBMenu, wx.ID_EXIT, u"Quit"+ u"\t" + u"CTRL-Q", wx.EmptyString, wx.ITEM_NORMAL )
		self.SolDBMenu.Append( self.quiteItem )

		self.SolDBMenuBar.Append( self.SolDBMenu, u"File" )

		self.SetMenuBar( self.SolDBMenuBar )


		self.Centre( wx.BOTH )

		# Connect Events
		self.Bind( wx.EVT_MENU, self.showAbout, id = self.aboutItem.GetId() )
		self.Bind( wx.EVT_MENU, self.onQuit, id = self.quiteItem.GetId() )

	def __del__( self ):
		pass


	# Virtual event handlers, override them in your derived class
	def showAbout( self, event ):
		event.Skip()

	def onQuit( self, event ):
		event.Skip()


###########################################################################
## Class SolDBPanel
###########################################################################

class SolDBPanel ( wx.Panel ):

	def __init__( self, parent, id = wx.ID_ANY, pos = wx.DefaultPosition, size = wx.Size( 549,499 ), style = wx.TAB_TRAVERSAL, name = wx.EmptyString ):
		wx.Panel.__init__ ( self, parent, id = id, pos = pos, size = size, style = style, name = name )

		mainSizer = wx.BoxSizer( wx.VERTICAL )

		decksFirstHSizer = wx.BoxSizer( wx.HORIZONTAL )

		self.userLbl = wx.StaticText( self, wx.ID_ANY, u"SFF User Name: ", wx.DefaultPosition, wx.DefaultSize, 0 )
		self.userLbl.Wrap( -1 )

		decksFirstHSizer.Add( self.userLbl, 0, wx.ALL, 5 )

		self.userCtrl = wx.TextCtrl( self, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.Size( 240,-1 ), 0 )
		self.userCtrl.SetToolTip( u"Username used on the solforgefusion.com website" )

		decksFirstHSizer.Add( self.userCtrl, 0, wx.ALL, 5 )


		mainSizer.Add( decksFirstHSizer, 0, wx.EXPAND, 5 )

		self.mainPage = wx.Panel( self, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.TAB_TRAVERSAL )
		SolDBMainSizer = wx.BoxSizer( wx.VERTICAL )

		self.SolDBTabs = wx.Notebook( self.mainPage, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, 0 )
		self.AnalyzeDeck = wx.Panel( self.SolDBTabs, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.TAB_TRAVERSAL )
		analyzeMainSizer = wx.BoxSizer( wx.VERTICAL )

		deckTypeCtrlChoices = [ u"Faction Half Deck", u"Fused Deck" ]
		self.deckTypeCtrl = wx.Choice( self.AnalyzeDeck, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, deckTypeCtrlChoices, 0 )
		self.deckTypeCtrl.SetSelection( 1 )
		analyzeMainSizer.Add( self.deckTypeCtrl, 0, wx.ALL, 5 )

		decksFirstHSizer1 = wx.BoxSizer( wx.HORIZONTAL )

		self.idLabel = wx.StaticText( self.AnalyzeDeck, wx.ID_ANY, u"Deck ID:", wx.DefaultPosition, wx.DefaultSize, 0 )
		self.idLabel.Wrap( -1 )

		decksFirstHSizer1.Add( self.idLabel, 0, wx.ALL, 5 )

		self.idCtrl = wx.TextCtrl( self.AnalyzeDeck, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.Size( 240,-1 ), 0 )
		self.idCtrl.SetToolTip( u"id of deck" )

		decksFirstHSizer1.Add( self.idCtrl, 0, wx.ALL, 5 )


		analyzeMainSizer.Add( decksFirstHSizer1, 1, wx.EXPAND, 5 )

		buttonHSizer = wx.BoxSizer( wx.HORIZONTAL )


		buttonHSizer.Add( ( 0, 0), 1, wx.EXPAND, 5 )

		self.AnalyzeBtn = wx.Button( self.AnalyzeDeck, wx.ID_ANY, u"Analyze", wx.DefaultPosition, wx.DefaultSize, 0 )

		self.AnalyzeBtn.SetBitmapPosition( wx.RIGHT )
		buttonHSizer.Add( self.AnalyzeBtn, 0, wx.ALL, 5 )


		analyzeMainSizer.Add( buttonHSizer, 1, wx.EXPAND, 5 )


		self.AnalyzeDeck.SetSizer( analyzeMainSizer )
		self.AnalyzeDeck.Layout()
		analyzeMainSizer.Fit( self.AnalyzeDeck )
		self.SolDBTabs.AddPage( self.AnalyzeDeck, u"Analyze Deck", True )
		self.EvalCollection = wx.Panel( self.SolDBTabs, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.TAB_TRAVERSAL )
		EvalMainSizer = wx.BoxSizer( wx.VERTICAL )

		self.createGraphCtrl = wx.CheckBox( self.EvalCollection, wx.ID_ANY, u"Create Graph", wx.DefaultPosition, wx.DefaultSize, 0 )
		self.createGraphCtrl.SetToolTip( u"Includes an extra card with faction logo for each faction in list, use it for minions or to seperate factions in the box" )

		EvalMainSizer.Add( self.createGraphCtrl, 0, wx.ALL, 5 )

		self.selectPairsCtrl = wx.CheckBox( self.EvalCollection, wx.ID_ANY, u"Create Top Pairs File", wx.DefaultPosition, wx.DefaultSize, 0 )
		self.selectPairsCtrl.SetToolTip( u"Includes an extra card with faction logo for each faction in list, use it for minions or to seperate factions in the box" )

		EvalMainSizer.Add( self.selectPairsCtrl, 0, wx.ALL, 5 )

		self.offlineCtrl = wx.CheckBox( self.EvalCollection, wx.ID_ANY, u"Offline Mode", wx.DefaultPosition, wx.DefaultSize, 0 )
		self.offlineCtrl.SetToolTip( u"Includes an extra card with faction logo for each faction in list, use it for minions or to seperate factions in the box" )

		EvalMainSizer.Add( self.offlineCtrl, 0, wx.ALL, 5 )

		filterHSizer = wx.BoxSizer( wx.HORIZONTAL )

		self.filterLbl = wx.StaticText( self.EvalCollection, wx.ID_ANY, u"Card Filter:", wx.DefaultPosition, wx.DefaultSize, 0 )
		self.filterLbl.Wrap( -1 )

		filterHSizer.Add( self.filterLbl, 0, wx.ALL, 5 )

		self.filterCtrl = wx.TextCtrl( self.EvalCollection, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.Size( 240,-1 ), 0 )
		self.filterCtrl.SetToolTip( u"Username used on the solforgefusion.com website" )

		filterHSizer.Add( self.filterCtrl, 0, wx.ALL, 5 )


		EvalMainSizer.Add( filterHSizer, 1, wx.EXPAND, 5 )

		buttonLabelHSizer = wx.BoxSizer( wx.HORIZONTAL )


		buttonLabelHSizer.Add( ( 0, 0), 1, wx.EXPAND, 5 )

		self.EvalBtn = wx.Button( self.EvalCollection, wx.ID_ANY, u"Evaluate", wx.DefaultPosition, wx.DefaultSize, 0 )

		self.EvalBtn.SetBitmapPosition( wx.RIGHT )
		buttonLabelHSizer.Add( self.EvalBtn, 0, wx.ALL, 5 )


		EvalMainSizer.Add( buttonLabelHSizer, 1, wx.EXPAND, 5 )


		self.EvalCollection.SetSizer( EvalMainSizer )
		self.EvalCollection.Layout()
		EvalMainSizer.Fit( self.EvalCollection )
		self.SolDBTabs.AddPage( self.EvalCollection, u"Evaluate Collection", False )

		SolDBMainSizer.Add( self.SolDBTabs, 0, wx.EXPAND |wx.ALL, 5 )


		self.mainPage.SetSizer( SolDBMainSizer )
		self.mainPage.Layout()
		SolDBMainSizer.Fit( self.mainPage )
		mainSizer.Add( self.mainPage, 1, wx.EXPAND |wx.ALL, 5 )


		self.SetSizer( mainSizer )
		self.Layout()

		# Connect Events
		self.AnalyzeBtn.Bind( wx.EVT_BUTTON, self.analyzeDeck )
		self.EvalBtn.Bind( wx.EVT_BUTTON, self.evalDecks )

	def __del__( self ):
		pass


	# Virtual event handlers, override them in your derived class
	def analyzeDeck( self, event ):
		event.Skip()

	def evalDecks( self, event ):
		event.Skip()


