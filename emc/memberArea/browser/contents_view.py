#-*- coding: UTF-8 -*-
from five import grok
from z3c.form import field
import json
from zope.event import notify
from Acquisition import aq_inner
from Acquisition import aq_parent
from zope.interface import Interface 
from zope.component import getMultiAdapter
from Products.CMFCore.utils import getToolByName
from plone.app.layout.navigation.interfaces import INavigationRoot
from plone.memoize.instance import memoize
from zope.interface import Interface
from plone.directives import dexterity
from plone.memoize.instance import memoize
from emc.memberArea.content.messagebox import IMessagebox
from emc.memberArea.content.outputbox import IOutputbox
from emc.memberArea.content.message import IMessage
from emc.memberArea.content.todo import ITodo
from emc.memberArea.content.favorite import IFavorite
from emc.memberArea.content.myfolder import IMyfolder
from emc.theme.interfaces import IThemeSpecific

from emc.memberArea.events import FavoriteEvent,UnFavoriteEvent
from emc.memberArea import sendMessage


from emc.memberArea import _

grok.templatedir('templates') 

class BaseView(grok.View):
    "emc memberArea base view"
    grok.context(Interface)
    grok.template('base_view')    
    grok.name('baseview')
    grok.require('zope2.View')    
    
    @memoize    
    def catalog(self):
        context = aq_inner(self.context)
        pc = getToolByName(context, "portal_catalog")
        return pc
    
    @memoize    
    def pm(self):
        context = aq_inner(self.context)
        pm = getToolByName(context, "portal_membership")
        return pm    
            
    @property
    def isEditable(self):
        return self.pm().checkPermission(permissions.ManagePortal,self.context)
    
    def canbeSend(self):
        return self.pm().checkPermission(sendMessage,self.context)        
    
    def getMessageUrl(self):
           
        hf = self.pm().getHomeFolder(self.pm().getAuthenticatedMember().getId())
#         import pdb
#         pdb.set_trace()
        box = hf['workspace']['messagebox']['outputbox']
        url = "%s/@@write_message" % box.absolute_url()     
        return url        
    

class MessageboxView(BaseView):
    "emc memberArea messagebox view"
    grok.context(IMessagebox)
    grok.template('messagebox_ajax_view')
    grok.name('ajax_view')
    grok.require('emc.memberArea.view_message')
    
    def update(self):
        # Hide the editable-object border
        self.request.set('disable_border', True)    
    
    @memoize    
    def allitems(self):
        """fetch all messages"""               
        messagebrains = self.catalog()(object_provides=IMessage.__identifier__, 
                                path="/".join(self.context.getPhysicalPath()),
                                              sort_order="reverse",
                                              sort_on="created")       
        return messagebrains
        
    def getMessagebrains(self,start=0,size=0):
        "return messags data"

        if size==0:
            braindata = self.allitems()
        else:
            braindata = self.catalog()(object_provides=IMessage.__identifier__, 
                                path="/".join(self.context.getPhysicalPath()),
                                              sort_order="reverse",
                                              sort_on="created",
                                              b_start= start,
                                              b_size=size)            
        return self.outputList(braindata)
    
    
    def outputList(self,braindata):
        """ output brains for template render
        """
        outhtml = ""
        brainnum = len(braindata)
#         import pdb
#         pdb.set_trace()
        obj = self.context
               #message content type just two status:"unreaded","readed"
        if obj.id == "messagebox":
            bsurl = obj.absolute_url() + "/outputbox"
        elif obj.id == "outputbox":
            bsurl = obj.absolute_url()
        else:
            bsurl = aq_parent(obj).absolute_url() + "/outputbox"
        answerurl = bsurl + "/@@write_message"       
        for i in braindata:
            objurl =  i.getURL()           
            id = i.id            
            name = i.Title # message object's title
            sender = i.Creator
            register_date = i.created.strftime('%Y-%m-%d')
            status = i.review_state                             

            delurl = "%s/delete_confirmation" % objurl                        
            out = """<tr class="row">
                  <td class="col-md-4">
                      <a href="%(url)s">
                         <span>%(name)s</span>
                      </a>
                  </td>                
                  <td class="col-md-2 text-left">%(sender)s
                  </td>
                  <td class="col-md-2">%(register_date)s
                  </td>
                  <td class="col-md-2 handler">""" % dict(url=objurl,
                                                          name=name,
                                                          sender=sender,
                                                          register_date=register_date)

            if status == "unreaded":
                out1 =""" 
                    <input type="checkbox" 
                                  id="%(id)s"
                                  data-state=%(status)s 
                                  class="iphone-style-checkbox hidden" 
                                  checked="checked"/>
                                  <span rel="%(id)s" class="iphone-style on">&nbsp;</span>""" \
                                   % dict (id=id,status=status)
            else:
                out1 = """
                    <input type="checkbox" 
                        id="%(id)s"
                        data-state=%(status)s 
                        class="iphone-style-checkbox hidden" />
                        <span rel="%(id)s" class="iphone-style off">&nbsp;</span>""" \
                        % dict (id=id,status=status)                                       
            out2 = """</td>
                  <td class="col-md-2">
                                    <div i18n:domain="plone" class="row">
                                        <div class="col-md-6 text-center">
                                        <a href="%(answerurl)s" class="link-overlay btn btn-success">
                                      <i class="icon-pencil icon-white"></i>回复</a>
                                  </div>
                                  <div class="col-md-6 text-center">
                                          <a href="%(delurl)s" class="link-overlay btn btn-danger">
                                      <i class="icon-trash icon-white"></i>删除</a>
                                  </div>
                                    </div>
                   </td>          
                  </tr>""" % dict(answerurl=answerurl,delurl=delurl)           
            outhtml = "%s%s%s%s" %(outhtml,out,out1,out2)
        return outhtml
    
    def pendingDefault(self,size=10):
        "计算缺省情况下，还剩多少条"
        total = len(self.allitems())
        if total > size:
            return total - size
        else:
            return 0          
        
    def search_multicondition(self,query):  
        return self.catalog()(query)         

class MessageAjaxSearch(grok.View):
    """AJAX action for ajax_view.
    """    

    grok.name('message_ajax')
    grok.context(IMessagebox)
    grok.layer(IThemeSpecific)
    # ajax response view should be called just by manager permission?
    grok.require('emc.memberArea.view_message')
          
    def render(self):
        searchview = getMultiAdapter((self.context, self.request),name=u"view")       
        datadic = self.request.form
        start = int(datadic['start']) # batch search start position
        size = int(datadic['size'])      # batch search size  
        # search all                         
        totalbrains = searchview.allitems()
        totalnum = len(totalbrains)
        # batch search 
#         import pdb
#         pdb.set_trace()        
        outhtml = searchview.getMessagebrains(start=start,size=size)
        data = self.output(start,size,totalnum, outhtml)
        self.request.response.setHeader('Content-Type', 'application/json')
        return json.dumps(data)       
       
    def output(self,start,size,totalnum,outhtml):
        "根据参数total,braindata,返回jason 输出"           
        data = {'searchresult': outhtml,'start':start,'size':size,'total':totalnum}
        return data
         
class MessageboxListView(MessageboxView):
     "emc memberArea messagebox load more view"
     
     grok.context(IMessagebox)
     grok.template('messagebox_listing')
     grok.name('view')
     grok.require('emc.memberArea.view_message')
     
class outputboxListView(MessageboxView):
     "emc memberArea messagebox view"
     
     grok.context(IOutputbox)
     grok.template('outputbox_listing')
     grok.name('view')
     grok.require('emc.memberArea.view_message')
     
     def outputList(self,braindata):
        """ output brains for template render
        """
        outhtml = ""
        brainnum = len(braindata)
#         import pdb
#         pdb.set_trace()
        obj = self.context
               #message content type just two status:"unreaded","readed"
        if obj.id == "messagebox":
            bsurl = obj.absolute_url() + "/outputbox"
        elif obj.id == "outputbox":
            bsurl = obj.absolute_url()
        else:
            bsurl = aq_parent(obj).absolute_url() + "/outputbox"
        answerurl = bsurl + "/@@write_message"       
        for i in braindata:
            objurl =  i.getURL()           
            id = i.id            
            name = i.Title # message object's title
            sender = i.Creator
            register_date = i.created.strftime('%Y-%m-%d')
#             status = i.review_state                             

            delurl = "%s/delete_confirmation" % objurl                        
            out = """<tr class="row">
                  <td class="col-md-6">
                      <a href="%(url)s">
                         <span>%(name)s</span>
                      </a>
                  </td>                
                  <td class="col-md-2 text-left">%(sender)s
                  </td>
                  <td class="col-md-2">%(register_date)s
                  </td>
                  """ % dict(url=objurl,
                                                          name=name,
                                                          sender=sender,
                                                          register_date=register_date)
                                      
            out2 = """
                  <td class="col-md-2">
                                  <div class="col-md-6 text-center">
                                          <a href="%(delurl)s" class="link-overlay btn btn-danger">
                                      <i class="icon-trash icon-white"></i>删除</a>
                                  </div>
                   </td>          
                  </tr>""" % dict(delurl=delurl)           
            outhtml = "%s%s%s" %(outhtml,out,out2)
        return outhtml
              
     
class TodoListView(MessageboxView):
     "emc memberArea todo listing view"
     
     grok.context(ITodo)
     grok.template('todo_listing')
     grok.name('view')
     grok.require('zope2.View')
     
     @memoize    
     def allitems(self):
        """fetch all messages"""               
        messagebrains = self.catalog()(review_status='pending', 
                                path="/".join(self.context.getPhysicalPath()),
                                              sort_order="reverse",
                                              sort_on="created")       
        return messagebrains     

     def getMessagebrains(self,start=0,size=0):
        "return messags data"


        if size==0:
            braindata = self.allitems()
        else:
            braindata = self.catalog()(review_status='pending',                                
                                              sort_order="reverse",
                                              sort_on="created",
                                              b_start= start,
                                              b_size=size)            
        return self.outputList(braindata)     
          
     def outputList(self,braindata):
        """ output brains for template render
        """
        outhtml = ""
        brainnum = len(braindata)
        obj = self.context
      
        for i in braindata:
            objurl =  i.getURL()           
            id = i.id            
            name = i.Title # message object's title
            description = i.Description
            sender = i.Creator
            register_date = i.created.strftime('%Y-%m-%d')
#             status = i.review_state                          
                        
            out = """<tr class="row">
                  <td class="col-md-4">
                      <a href="%(url)s">
                         <span>%(name)s</span>
                      </a>
                  </td>                
                  <td class="col-md-6 text-left">%(description)s
                  </td>
                  <td class="col-md-2">%(register_date)s
                  </td>""" % dict(url=objurl,
                                                          name=name,
                                                          description=description,
                                                          register_date=register_date)                 
                                     
         
            outhtml = "%s%s" %(outhtml,out)
        return outhtml

class FavoriteListView(MessageboxView):
     "emc memberArea todo listing view"
     
     grok.context(IFavorite)
     grok.template('myfavoritefolder')
     grok.name('view')
     grok.require('emc.memberArea.view_favorite')
     
     def getFavoriteItemsId(self):

         userobject = self.pm().getAuthenticatedMember()
         userid = userobject.getId()
         fav = self.pm().getHomeFolder(userid)['workspace']['favorite']
         favoritelist = list(getattr(fav,'myfavorite',[]))
         return favoritelist         
     
     @memoize    
     def allitems(self):
        """fetch all messages"""
                     
        messagebrains = self.catalog()({
                     'UID': self.getFavoriteItemsId(),
                     'sort_order': 'reverse',
                     'sort_on': 'modified'})      
        return messagebrains     

     def getMessagebrains(self,start=0,size=0):
        "return messags data"

        from plone import api
        current = api.user.get_current()
        if size==0:
            braindata = self.allitems()
        else:
            braindata = self.catalog()({
                                 'UID': self.getFavoriteItemsId(),
                                 'sort_order': 'reverse',
                                 'sort_on': 'modified',
                                 'b_start': start,
                                 'b_size': size})            
        return self.outputList(braindata)     
          
     def outputList(self,braindata):
        """ output brains for template render
        """
        outhtml = ""
        brainnum = len(braindata)
        obj = self.context
      
        for i in braindata:
            objurl =  i.getURL()           
            id = i.id
            uid = i.UID            
            name = i.Title # message object's title
            description = i.Description
            sender = i.Creator
            register_date = i.created.strftime('%Y-%m-%d')
#             status = i.review_state                          
                        
            out = """<tr class="row">
                  <td class="col-md-8">
                      <a href="%(url)s">
                         <span>%(name)s</span>
                      </a>
                  </td>                
                  <td class="col-md-2 text-left">%(register_date)s
                  </td>
                  <td class="col-md-2 unfavorite" rel="%(uid)s" data-ajax-target="%(url)s">
                  <a href="#" class="link-overlay btn btn-danger">
                                      <i class="icon-trash icon-white"></i>删除</a>
                  </td>""" % dict(url=objurl,name=name,uid=uid,register_date=register_date)                 
                                     
         
            outhtml = "%s%s" %(outhtml,out)
        return outhtml        
       
class MyfolderListView(MessageboxView):
     "emc memberArea personal netwok storage listing view"
     
     grok.context(IMyfolder)
     grok.template('myfolder')
     grok.name('view')
     grok.require('emc.memberArea.view_favorite')

     @memoize    
     def allitems(self):
        """fetch all messages"""               
        messagebrains = self.catalog()( 
                                path="/".join(self.context.getPhysicalPath()),
                                              sort_order="reverse",
                                              sort_on="created")       
        return messagebrains
        
     def getMessagebrains(self,start=0,size=0):
        "return messags data"

        if size==0:
            braindata = self.allitems()
        else:
            braindata = self.catalog()(
                                path="/".join(self.context.getPhysicalPath()),
                                              sort_order="reverse",
                                              sort_on="created",
                                              b_start= start,
                                              b_size=size)
            brains = [brain for brain in braindata if brain.id !="myfolder"]            
        return self.outputList(brains)
    
     def outputList(self,braindata):
        """ output brains for template render
        """
        outhtml = ""
        brainnum = len(braindata)
        obj = self.context
      
        for i in braindata:
            objurl =  i.getURL()           
            id = i.id           
            name = i.Title # message object's title
            description = i.Description
            sender = i.Creator
            register_date = i.created.strftime('%Y-%m-%d')
            delurl = "%s/delete_confirmation" % objurl                           
                        
            out = """<tr class="row">
                  <td class="col-md-8">
                      <a href="%(url)s">
                         <span>%(name)s</span>
                      </a>
                  </td>                
                  <td class="col-md-2 text-left">%(register_date)s
                  </td>
                  <td class="col-md-2">
                  <a href="%(delurl)s" class="link-overlay btn btn-danger">
                                      <i class="icon-trash icon-white"></i>删除</a>
                  </td>""" % dict(url=objurl,name=name,delurl=delurl,register_date=register_date)                                                             
            outhtml = "%s%s" %(outhtml,out)
        return outhtml    

class MessageMore(grok.View):
    """message list view AJAX action for click more. default batch size is 10.
    """
   
#     grok.context(IMessagebox)
    grok.context(Interface)    
    grok.name('more')
    grok.layer(IThemeSpecific)
    grok.require('zope2.View')            
    
    def render(self):
        form = self.request.form
        formst = form['formstart']
        formstart = int(formst)*10 
        nextstart = formstart + 10                
        more_view = getMultiAdapter((self.context, self.request),name=u"view")
        favoritenum = len(more_view.allitems())
        
        if nextstart >= favoritenum :
            ifmore =  1
            pending = 0
        else :
            ifmore = 0  
            pending = favoritenum - nextstart          

        pending = "%s" % (pending)          
        outhtml = more_view.getMessagebrains(formstart,10)            
        data = {'outhtml': outhtml,'pending':pending,'ifmore':ifmore}
    
        self.request.response.setHeader('Content-Type', 'application/json')
        return json.dumps(data)
    
class MessageState(grok.View):
    "receive front ajax data,change member workflow status"
    grok.context(IMessagebox)
    grok.name('ajaxmessagestate')
    grok.layer(IThemeSpecific)
    grok.require('zope2.View')
    
    def render(self):
        data = self.request.form
        id = data['id']
        state = data['state']        
        catalog = getToolByName(self.context, 'portal_catalog')
        obj = catalog({'object_provides': IMessage.__identifier__,
                       'path':"/".join(self.context.getPhysicalPath()), 
                       "id":id})[0].getObject()        
        portal_workflow = getToolByName(self.context, 'portal_workflow')
# obj current status        
        if state == "unreaded" : # this is a new account
            try:
                portal_workflow.doActionFor(obj, 'done')                   
                result = True
            except:
                result = False
        elif state == "readed":
            try:
                portal_workflow.doActionFor(obj, 'undo')
                result = True
            except:
                result = False
        else:
            result = False         
        obj.reindexObject()
        self.request.response.setHeader('Content-Type', 'application/json')
        return json.dumps(result)                          
    
class MessageView(BaseView):
    "emc memberArea message view"
    grok.context(IMessage)
    grok.template('message_view')
    grok.name('view')
    grok.require('emc.memberArea.view_message')  
 
class FavoriteAjax(grok.View):
    "receive front ajax data,trigle UnFavoriteEvent"
    grok.context(IFavorite)
    grok.name('ajax')
    grok.layer(IThemeSpecific)
    grok.require('emc.memberArea.view_favorite')
    
    def render(self):
        data = self.request.form
        uid = data['uid']      
        catalog = getToolByName(self.context, 'portal_catalog')
#         import pdb
#         pdb.set_trace()
        obj = catalog(UID=uid)[0].getObject()
        try:
            notify(UnFavoriteEvent(obj))
            result = 1
        except:
            result = 0           
        data = {"result":result}
        self.request.response.setHeader('Content-Type', 'application/json')
        return json.dumps(data)
 
        
