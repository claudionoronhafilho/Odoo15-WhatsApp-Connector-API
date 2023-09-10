# See LICENSE file for full copyright and licensing details.

import ast
import base64
from odoo import fields, models, _, sql_db, api, tools
from odoo.tools.mimetypes import guess_mimetype
from odoo.exceptions import Warning, UserError
from datetime import datetime
import html2text
import threading
import requests
import json
import logging

_logger = logging.getLogger(__name__)

class MailMessage(models.Model):
    _inherit = 'mail.message'
    
    message_type = fields.Selection(selection_add=[('whatsapp', 'Whatsapp')], ondelete={'whatsapp': 'set default'})    
    whatsapp_server_id = fields.Many2one('ir.whatsapp_server', string='Whatsapp Server')
    whatsapp_method = fields.Char('Method', default='sendMessage')
    whatsapp_status = fields.Selection([('pending','Pending'),('send', 'Sent'),('error', 'Error')], default='pending', string='Status')
    whatsapp_response = fields.Text('Response', readonly=True)
    whatsapp_data = fields.Text('Data', readonly=False)
    whatsapp_chat_id = fields.Char(string='ChatId')

    # @api.model
    # def create(self, vals):
    #     if vals.get('whatsapp_data'):
    #         vals['whatsapp_data'] = str(vals['whatsapp_data']).replace("'",'*').replace('"',"*")
    #     return super(MailMessage, self).create(vals)
    
    @api.model
    def _resend_whatsapp_message_resend(self, KlikApi):
        try:
            #new_cr = sql_db.db_connect(self.env.cr.dbname).cursor()
            #uid, context = self.env.uid, self.env.context
            new_cr = self.pool.cursor()
            self = self.with_env(self.env(cr=new_cr))
            with tools.mute_logger('odoo.sql_db'):
                #self.env = api.Environment(new_cr, uid, context)
                MailMessage = self.env['mail.message'].search([('message_type','=','whatsapp'),('whatsapp_status', '=', 'pending')], limit=50)
                get_version = self.env["ir.module.module"].sudo().search([('name','=','base')], limit=1).latest_version
                for mail in MailMessage:
                    data = json.loads(str(mail.whatsapp_data.replace("'",'"')))
                    message_data = {
                        'chatId': mail.whatsapp_chat_id,
                        'body': html2text.html2text(mail.body),
                        'phone': data['phone'] if 'phone' in data else '',
                        'origin': data['origin'] if 'origin' in data else '',
                        'link': data['link'] if 'link' in data else '',
                        'get_version': get_version,
                    }
                    if mail.whatsapp_method == 'sendFile' and mail.attachment_ids:
                        attach = [att for att in mail.attachment_ids][0]#.datas
                        mimetype = guess_mimetype(base64.b64decode(attach.datas))
                        if mimetype == 'application/octet-stream':
                            mimetype = 'video/mp4'
                        str_mimetype = 'data:' + mimetype + ';base64,'
                        attachment = str_mimetype + str(attach.datas.decode("utf-8"))
                        message_data.update({'body': attachment, 'filename': [att for att in mail.attachment_ids][0].name, 'caption': data['caption']})
                    data_message = json.dumps(message_data)
                    send_message = KlikApi.post_request(method=mail.whatsapp_method, data=data_message)
                    if send_message.get('message')['sent']:
                        mail.whatsapp_status = 'send'
                        mail.whatsapp_response = send_message
                        _logger.warning('Success send Message to WhatsApp number %s', data['phone'])
                    else:
                        mail.whatsapp_status = 'error'
                        mail.whatsapp_response = send_message
                        _logger.warning('Failed send Message to WhatsApp number %s', data['phone'])
                    new_cr.commit()
        finally:
            self._cr.rollback()
            self._cr.close()

    @api.model
    def resend_whatsapp_mail_message(self):
        """Resend whatsapp error message via threding.""" 
        WhatsappServer = self.env['ir.whatsapp_server']
        whatsapp_ids = WhatsappServer.search([('status','=','authenticated')], order='sequence asc')
        #if len(whatsapp_ids) == 1:            
        for wserver in whatsapp_ids.filtered(lambda ws: not ast.literal_eval(str(ws.message_response))['block']):
            #company_id = self.env.user.company_id
            if wserver.status != 'authenticated':
                _logger.warning('Whatsapp Authentication Failed!\nConfigure Whatsapp Configuration in General Setting.')
            KlikApi = wserver.klikapi()
            KlikApi.auth()
            thread_start = threading.Thread(target=self._resend_whatsapp_message_resend(KlikApi))
            thread_start.start()
        return True