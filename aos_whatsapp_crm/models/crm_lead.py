# See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, sql_db, _
from odoo.tools.mimetypes import guess_mimetype
import requests
import json
import base64
from datetime import datetime
import time
import html2text
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class Lead(models.Model):
    _inherit = "crm.lead"
    
    whatsapp = fields.Char('Whatsapp', track_visibility='onchange', track_sequence=5, default=0)
    chat_id = fields.Char(string='ChatID')
    
    def _formatting_mobile_number(self):
        for rec in self:
            module_rec = self.env['ir.module.module'].sudo().search_count([
                ('name', '=', 'crm_phone_validation'),
                ('state', '=', 'installed')])
            
            country_code = str(rec.country_id.phone_code) if rec.country_id else str(self.company_id.country_id.phone_code)
            country_count = len(str(rec.country_id.phone_code))
            whatsapp_number = rec.whatsapp
            if rec.whatsapp[:country_count] == str(rec.country_id.phone_code):
                whatsapp_number = rec.whatsapp
            elif rec.whatsapp[0] == '0':
                if rec.whatsapp[1:country_count+1] == str(rec.country_id.phone_code):
                    #COUNTRY CODE UDH DIDEPAN
                    whatsapp_number = rec.whatsapp[1:]
                else:
                    whatsapp_number = country_code + rec.whatsapp[1:]
            return whatsapp_number
            #print ('=_formatting_mobile_number=',rec.whatsapp[1:],rec.whatsapp[0])
            # return module_rec and re.sub("[^0-9]", '', rec.whatsapp) or \
            #     str(rec.country_id.phone_code
            #         ) + rec.whatsapp[1:] if rec.whatsapp[0] == '0' else rec.whatsapp
                    
    # def get_link(self):
    #     for crm in self:
    #         base_url = crm.get_base_url()
    #         share_url = crm._get_share_url(redirect=True, signup_partner=True)
    #         url = base_url + share_url
    #         return url
        
    def _get_whatsapp_server(self):
        WhatsappServer = self.env['ir.whatsapp_server']
        whatsapp_ids = WhatsappServer.search([('status','=','authenticated')], order='sequence asc', limit=1)
        if len(whatsapp_ids) == 1:
            return whatsapp_ids
        return False
    
    def send_whatsapp_automatic(self):
        for crm in self:
            #print ('==send_whatsapp_automatic==',crm)
            new_cr = sql_db.db_connect(self.env.cr.dbname).cursor()
            MailMessage = self.env['mail.message']
            WhatsappComposeMessage = self.env['whatsapp.compose.message']
            template_id = self.env.ref('aos_whatsapp_crm.crm_lead_update_status', raise_if_not_found=False)
            if self._get_whatsapp_server() and self._get_whatsapp_server().status == 'authenticated':
                KlikApi = self._get_whatsapp_server().klikapi()
                KlikApi.auth()       
                template = template_id.generate_email(crm.id)
                body = template.get('body')
                subject = template.get('subject')
                try:
                    #print ('==PARTNER==',crm.partner_id.name,crm.partner_name)
                    body = body.replace('_PARTNER_', crm.partner_id.name or crm.partner_name or crm.contact_name or '')
                    #print ('====',body)
                except:
                    _logger.warning('Failed to send Message to WhatsApp number %s', crm.whatsapp)
                            
                attachment_ids = []
                chatIDs = []
                message_data = {}
                send_message = {}
                status = 'error'
                partners = self.env['res.partner']
                if crm.partner_id:
                    partners = crm.partner_id
                    # if crm.partner_id.child_ids:
                    #     #ADDED CHILD FROM PARTNER
                    #     for partner in sale.partner_id.child_ids:
                    #         partners += partner
                if partners:
                    #print ('==partners==',partners)
                    for partner in partners:
                        if partner.country_id and partner.whatsapp:
                            #SEND MESSAGE
                            whatsapp = partner._formatting_mobile_number()
                            message_data = {
                                'method': 'sendMessage',
                                'phone': whatsapp,
                                'body': html2text.html2text(body),# + crm.get_link(),
                                'origin': crm.name,
                                'link': ''#crm.get_link(),
                            }                        
                            if partner.chat_id:
                                message_data.update({'chatId': partner.chat_id, 'phone': '', 'origin': crm.name, 'link': ''})
                            #data_message = json.dumps(message_data)
                            #send_message = KlikApi.post_request(method='sendMessage', data=data_message)
                            send_message = {}
                            status = 'pending'
                            # if send_message.get('message')['sent']:
                            #     chatID = send_message.get('chatID')
                            #     status = 'send'
                            #     partner.chat_id = chatID
                            #     chatIDs.append(chatID)
                            #     _logger.warning('Success to send Message to WhatsApp number %s', whatsapp)
                            # else:
                            #     status = 'error'
                            #     _logger.warning('Failed to send Message to WhatsApp number %s', whatsapp)
                            chatIDs = None#';'.join(chatIDs)
                            vals = WhatsappComposeMessage._prepare_mail_message(self.env.user.partner_id.id, chatIDs, crm and crm.id,  'crm.lead', body, message_data, subject, [partner.id], attachment_ids, send_message, status)
                            MailMessage.sudo().create(vals)
                            new_cr.commit()
                            #new_cr.commit()
                else:
                    #print ('==CRM==',crm.country_id,crm.whatsapp)
                    if crm.country_id and crm.whatsapp:
                        #SEND MESSAGE
                        whatsapp = crm._formatting_mobile_number()
                        message_data = {
                            'method': 'sendMessage',
                            'phone': whatsapp,
                            'body': html2text.html2text(body),# + crm.get_link(),
                            'origin': crm.name,
                            'link': '',#crm.get_link(),
                        }                        
                        if crm.chat_id:
                            message_data.update({'chatId': crm.chat_id, 'phone': '', 'origin': crm.name, 'link': ''})
                        #data_message = json.dumps(message_data)
                        #send_message = KlikApi.post_request(method='sendMessage', data=data_message)
                        send_message = {}
                        status = 'pending'
                        #print ('===send_message=',send_message)
                        # if send_message.get('message')['sent']:
                        #     chatID = send_message.get('chatID')
                        #     status = 'send'
                        #     crm.chat_id = chatID
                        #     chatIDs.append(chatID)
                        #     _logger.warning('Success to send Message to WhatsApp number %s', whatsapp)
                        # else:
                        #     status = 'error'
                        #     _logger.warning('Failed to send Message to WhatsApp number %s', whatsapp)
                        # new_cr.commit()
                        chatIDs = None#';'.join(chatIDs)
                        vals = WhatsappComposeMessage._prepare_mail_message(self.env.user.partner_id.id, chatIDs, crm and crm.id,  'crm.lead', body, message_data, subject, [crm.id], attachment_ids, send_message, status)
                        MailMessage.sudo().create(vals)
                        new_cr.commit()
                # AllchatIDs = ';'.join(chatIDs)
                # vals = WhatsappComposeMessage._prepare_mail_message(self.env.user.partner_id.id, AllchatIDs, crm and crm.id,  'crm.lead', body, message_data, subject, partners.ids, attachment_ids, send_message, status)
                # MailMessage.sudo().create(vals)
                # new_cr.commit()
                #time.sleep(3)