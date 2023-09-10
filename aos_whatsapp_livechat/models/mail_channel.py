from odoo import api, fields, models, _
import requests
import json
import logging
import re
from odoo import tools
from odoo.exceptions import UserError, ValidationError
_logger = logging.getLogger(__name__)


class MailThread(models.AbstractModel):
    _inherit = 'mail.thread'

    @api.returns('mail.message', lambda value: value.id)
    def message_post(self, **kwargs):
        if not self.env.user:
            #GET PUBLIC USER WHEN EMPTY
            self.env.user = self.env['res.users'].sudo().search([('active','=',False),('login','=','public')], limit=1)
        #print ('==MailThread==',self.env.user)
        return super(MailThread, self).message_post(**kwargs)

class MailMessage(models.Model):
    _inherit = 'mail.message'

    whatsapp_numbers = fields.Char()

class ChannelPartner(models.Model):
    _inherit = 'mail.channel.partner'

    @api.model_create_multi
    def create(self, vals_list):
        """Similar access rule as the access rule of the mail channel.

        It can not be implemented in XML, because when the record will be created, the
        partner will be added in the channel and the security rule will always authorize
        the creation.
        """
        #print ('===CHANNEL PARTNER==',vals_list)
        if len(vals_list) == 2:
            if not vals_list[1]['partner_id']:
                partner_id = self.env['res.users'].sudo().search([('active','=',False),('login','=','public')], limit=1)
                vals_list[1].update({'partner_id': partner_id.id})
        return super(ChannelPartner, self).create(vals_list)

class mailChannel(models.Model):
    _inherit = 'mail.channel'

    senderkeyhash = fields.Char()
    recipientkeyhash = fields.Char()
    #path_id = fields.Many2one('api.rest.path', string="Whatsapp Path")
    
    @api.returns('mail.message', lambda value: value.id)
    def message_post(self, *, message_type='notification', **kwargs):
        message = super(mailChannel, self).message_post(**kwargs)
        #print ('===message_post==',self._context)
        if not self._context.get('from_odoobot') and self._context.get('uid'):
            self.send_whatsapp_message(self.message_ids, kwargs, message)
        return message

    def convert_email_from_to_name(self, str1):
        result = re.search('"(.*)"', str1)
        return result.group(1)

    def custom_html2plaintext(self, html):
        html = re.sub('<br\s*/?>', '\n', html)
        html = re.sub('<.*?>', ' ', html)
        return html

    def send_whatsapp_message(self, message_ids, kwargs, message_id):
        partner_id = False
        WhatsappServer = self.env['ir.whatsapp_server']
        whatsapp_id = WhatsappServer.search([('status','=','authenticated')], order='sequence asc', limit=1)
        whatsapp_endpoint = 'https://klikodoo.id/api/wa'
        whatsapp_instance = whatsapp_id.klik_key
        whatsapp_token = whatsapp_id.klik_secret
        # if 'author_id' in kwargs and kwargs.get('author_id'):
        #     partner_id = self.channel_last_seen_partner_ids
        #     partner_id = self.env['res.partner'].search([('id', '=', kwargs.get('author_id'))])
        partner_ids = message_ids.mapped('author_id')
        whatsapp_numbers = list(filter(None, [*set(message_ids.mapped('whatsapp_numbers'))]))
        print ('==whatsapp_numbers==',whatsapp_numbers,partner_ids)
        if whatsapp_numbers:#partner_ids and message_id.author_id and not partner_id:
            #print ('-channel_last_seen_partner_ids--',self.channel_last_seen_partner_ids,self.channel_partner_ids)
            #print ('--send_whatsapp_message-from livechat to whatsapp-client',partner_ids, list(filter(None, [*set(whatsapp_numbers)])), kwargs, message_id)
            #partner.user_ids and all(user.has_group('base.group_user') for user in partner.user_ids)
            #partners = partner_ids.filtered(lambda p: p != message_id.author_id)
            #print ('===partner_id===',partner_id)
            #Param = self.env['res.config.settings'].sudo().get_values()
            #no_phone_partners = []
            invalid_whatsapp_number_partner = []
            if whatsapp_endpoint and whatsapp_token:
                status_url = whatsapp_endpoint + '/auth/' + whatsapp_instance + '/' + whatsapp_token + '/status'
                #print ('=status_url==',status_url,partner_id)
                status_response = requests.get(status_url, data=json.dumps({}), headers={'Content-Type': 'application/json'})
                json_response_status = json.loads(status_response.text)['result']
                # status_url = param.get('whatsapp_endpoint') + '/status?token=' + param.get('whatsapp_token')
                # status_response = requests.get(status_url)
                # json_response_status = json.loads(status_response.text)
                #print ('-send_whatsapp_message-',status_response,json_response_status,partner_id,partner_ids,partner_id.name,partner_id.country_id.phone_code, partner_id.mobile,partner_id.whatsapp)
                for whatsapp_number in whatsapp_numbers:
                    if (status_response.status_code == 200 or status_response.status_code == 201) and json_response_status['accountStatus'] == 'authenticated':
                    #if partner_id.country_id.phone_code and partner_id.whatsapp:
                        #whatsapp_msg_number = partner_id.whatsapp
                        # whatsapp_msg_number_without_space = whatsapp_msg_number.replace(" ", "");
                        # whatsapp_msg_number_without_strip = whatsapp_msg_number_without_space.replace("-", "")
                        # whatsapp_msg_number_without_code = whatsapp_msg_number_without_strip.replace(
                        #     '+' + str(partner_id.country_id.phone_code), "")
                        # phone_exists_url = param.get('whatsapp_endpoint') + '/checkPhone?token=' + param.get('whatsapp_token') + '&phone=' + str(partner_id.country_id.phone_code) + "" + whatsapp_msg_number_without_code
                        # phone_exists_response = requests.get(phone_exists_url)
                        # json_response_phone_exists = json.loads(phone_exists_response.text)
                        # phone_exists_url = whatsapp_endpoint + '/check/' + whatsapp_instance + '/' + whatsapp_token
                        # phone_exists_response = requests.get(phone_exists_url, data=json.dumps({'phone': str(partner_id.country_id.phone_code) + whatsapp_msg_number_without_code}), headers={'Content-Type': 'application/json'})
                        # json_response_phone_exists = json.loads(phone_exists_response.text)['result']
                        # print ('==phone_exists_response==',phone_exists_url,str(partner_id.country_id.phone_code) + whatsapp_msg_number_without_code,phone_exists_response,phone_exists_response.status_code,json_response_phone_exists)
                        # if (phone_exists_response.status_code == 200 or phone_exists_response.status_code == 201) and json_response_phone_exists['result'] == 'exists':
                        #_logger.info("\nPartner phone exists")
                        # url = param.get('whatsapp_endpoint') + '/sendMessage?token=' + param.get('whatsapp_token')
                        # headers = {
                        #     "Content-Type": "application/json",
                        # }
                        url = whatsapp_endpoint + '/post'
                        headers = {"Content-Type": "application/json"}
                        html_to_plain_text = self.custom_html2plaintext(kwargs.get('body'))

                        if kwargs.get('email_from'):
                            if '<' in kwargs.get('email_from') and '>' in kwargs.get('email_from'):
                                tmp_dict = {
                                    'params' : {
                                        "phone": whatsapp_number,
                                        "body": self.convert_email_from_to_name(kwargs.get('email_from'))+''+ str(self.id) + ': '+ html_to_plain_text,
                                        'instance': whatsapp_instance,
                                        'key': whatsapp_token,
                                        'method': 'sendMessage',
                                    }
                                }
                            else:
                                tmp_dict = {
                                    'params' : {
                                        "phone": whatsapp_number,
                                        "body": kwargs.get('email_from')+ '' + str(self.id) + ': ' + html_to_plain_text,
                                        'instance': whatsapp_instance,
                                        'key': whatsapp_token,
                                        'method': 'sendMessage',
                                    }
                                }
                        else:
                            tmp_dict = {
                                'params' : {
                                    "phone": whatsapp_number,
                                    "body": html_to_plain_text,
                                    'instance': whatsapp_instance,
                                    'key': whatsapp_token,
                                    'method': 'sendMessage',
                                }
                            }
                        print ('----tmp_dict---',tmp_dict)
                        response = requests.post(url, json.dumps(tmp_dict), headers=headers)
                        if response.status_code == 201 or response.status_code == 200:
                            _logger.info("\nSend Message successfully")
                            response_dict = response.json()
                                #message_id.with_context({'from_odoobot': True}).write({'whatsapp_message_id': response_dict.get('id')})
                            # else:
                            #     invalid_whatsapp_number_partner.append(partner_id.name)
                        # else:
                        #     no_phone_partners.append(partner_id.name)
                    else:
                        raise UserError(_('Please authorize your mobile number with klikodoo'))
            if len(invalid_whatsapp_number_partner) >= 1:
                raise UserError(_('Please add valid whatsapp number for %s customer')% ', '.join(invalid_whatsapp_number_partner))

    # def send_whatsapp_message(self, partner_ids, kwargs, message_id):
    #     print ('--send_whatsapp_message--',partner_ids, kwargs, message_id)
    #     partner_id = False
    #     WhatsappServer = self.env['ir.whatsapp_server']
    #     whatsapp_id = WhatsappServer.search([('status','=','authenticated')], order='sequence asc', limit=1)
    #     whatsapp_endpoint = 'https://klikodoo.id/api/wa'
    #     whatsapp_instance = whatsapp_id.klik_key
    #     whatsapp_token = whatsapp_id.klik_secret
    #     if 'author_id' in kwargs and kwargs.get('author_id'):
    #         partner_id = self.env['res.partner'].search([('id', '=', kwargs.get('author_id'))])
    #     if message_id.author_id and not partner_id:
    #         partner_id = message_id.author_id
    #         #print ('===partner_id===',partner_id)
    #         #Param = self.env['res.config.settings'].sudo().get_values()
    #         no_phone_partners = []
    #         invalid_whatsapp_number_partner = []
    #         if whatsapp_endpoint and whatsapp_id.klik_secret:
    #             status_url = whatsapp_endpoint + '/auth/' + whatsapp_instance + '/' + whatsapp_token + '/status'
    #             print ('=status_url==',status_url)
    #             status_response = requests.get(status_url, data=json.dumps({}), headers={'Content-Type': 'application/json'})
    #             json_response_status = json.loads(status_response.text)['result']
    #             # status_url = param.get('whatsapp_endpoint') + '/status?token=' + param.get('whatsapp_token')
    #             # status_response = requests.get(status_url)
    #             # json_response_status = json.loads(status_response.text)
    #             print ('-send_whatsapp_message-',json_response_status,partner_id,partner_id.name,partner_id.country_id.phone_code, partner_id.mobile)
    #             if (status_response.status_code == 200 or status_response.status_code == 201) and json_response_status['accountStatus'] == 'authenticated':
    #                 if partner_id.country_id.phone_code and partner_id.mobile:
    #                     whatsapp_msg_number = partner_id.mobile
    #                     whatsapp_msg_number_without_space = whatsapp_msg_number.replace(" ", "");
    #                     whatsapp_msg_number_without_strip = whatsapp_msg_number_without_space.replace("-", "")
    #                     whatsapp_msg_number_without_code = whatsapp_msg_number_without_strip.replace(
    #                         '+' + str(partner_id.country_id.phone_code), "")
    #                     # phone_exists_url = param.get('whatsapp_endpoint') + '/checkPhone?token=' + param.get('whatsapp_token') + '&phone=' + str(partner_id.country_id.phone_code) + "" + whatsapp_msg_number_without_code
    #                     # phone_exists_response = requests.get(phone_exists_url)
    #                     # json_response_phone_exists = json.loads(phone_exists_response.text)
    #                     # phone_exists_url = whatsapp_endpoint + '/check/' + whatsapp_instance + '/' + whatsapp_token
    #                     # phone_exists_response = requests.get(phone_exists_url, data=json.dumps({'phone': str(partner_id.country_id.phone_code) + whatsapp_msg_number_without_code}), headers={'Content-Type': 'application/json'})
    #                     # json_response_phone_exists = json.loads(phone_exists_response.text)['result']
    #                     # print ('==phone_exists_response==',phone_exists_url,str(partner_id.country_id.phone_code) + whatsapp_msg_number_without_code,phone_exists_response,phone_exists_response.status_code,json_response_phone_exists)
    #                     # if (phone_exists_response.status_code == 200 or phone_exists_response.status_code == 201) and json_response_phone_exists['result'] == 'exists':
    #                     _logger.info("\nPartner phone exists")
    #                     # url = param.get('whatsapp_endpoint') + '/sendMessage?token=' + param.get('whatsapp_token')
    #                     # headers = {
    #                     #     "Content-Type": "application/json",
    #                     # }
    #                     url = whatsapp_endpoint + '/post'
    #                     headers = {"Content-Type": "application/json"}
    #                     html_to_plain_text = self.custom_html2plaintext(kwargs.get('body'))

    #                     if kwargs.get('email_from'):
    #                         if '<' in kwargs.get('email_from') and '>' in kwargs.get('email_from'):
    #                             tmp_dict = {
    #                                 'params' : {
    #                                     "phone": str(partner_id.country_id.phone_code) + "" + whatsapp_msg_number_without_code,
    #                                     "body": self.convert_email_from_to_name(kwargs.get('email_from'))+''+ str(self.id) + ': '+ html_to_plain_text,
    #                                     'instance': whatsapp_instance,
    #                                     'key': whatsapp_token,
    #                                     'method': 'sendMessage',
    #                                 }
    #                             }
    #                         else:
    #                             tmp_dict = {
    #                                 'params' : {
    #                                     "phone": str(
    #                                         partner_id.country_id.phone_code) + "" + whatsapp_msg_number_without_code,
    #                                     "body": kwargs.get('email_from')+ '' + str(self.id) + ': ' + html_to_plain_text,
    #                                     'instance': whatsapp_instance,
    #                                     'key': whatsapp_token,
    #                                     'method': 'sendMessage',
    #                                 }
    #                             }
    #                     else:
    #                         tmp_dict = {
    #                             'params' : {
    #                                 "phone": str(
    #                                     partner_id.country_id.phone_code) + "" + whatsapp_msg_number_without_code,
    #                                 "body": html_to_plain_text,
    #                                 'instance': whatsapp_instance,
    #                                 'key': whatsapp_token,
    #                                 'method': 'sendMessage',
    #                             }
    #                         }
    #                     print ('----tmp_dict---',tmp_dict)
    #                     response = requests.post(url, json.dumps(tmp_dict), headers=headers)
    #                     if response.status_code == 201 or response.status_code == 200:
    #                         _logger.info("\nSend Message successfully")
    #                         response_dict = response.json()
    #                         #message_id.with_context({'from_odoobot': True}).write({'whatsapp_message_id': response_dict.get('id')})
    #                     # else:
    #                     #     invalid_whatsapp_number_partner.append(partner_id.name)
    #                 else:
    #                     no_phone_partners.append(partner_id.name)
    #             else:
    #                 raise UserError(_('aPlease authorize your mobile number with chat api'))
    #         if len(invalid_whatsapp_number_partner) >= 1:
    #             raise UserError(_('Please add valid whatsapp number for %s customer')% ', '.join(invalid_whatsapp_number_partner))
    #     else:
    #         no_phone_partners = []
    #         invalid_whatsapp_number_partner = []
    #         for partner_id in partner_ids:
    #             if whatsapp_endpoint and whatsapp_token:
    #                 status_url = whatsapp_endpoint + '/auth/' + whatsapp_instance + '/' + whatsapp_token + '/status'
    #                 status_response = requests.get(status_url, data=json.dumps({}), headers={'Content-Type': 'application/json'})
    #                 json_response_status = json.loads(status_response.text)['result']
    #                 # status_url = param.get('whatsapp_endpoint') + '/status?token=' + param.get('whatsapp_token')
    #                 # status_response = requests.get(status_url)
    #                 # json_response_status = json.loads(status_response.text)
    #                 if (status_response.status_code == 200 or status_response.status_code == 201) and json_response_status[
    #                     'accountStatus'] == 'authenticated':
    #                     if partner_id.country_id.phone_code and partner_id.mobile:
    #                         whatsapp_msg_number = partner_id.mobile
    #                         whatsapp_msg_number_without_space = whatsapp_msg_number.replace(" ", "");
    #                         whatsapp_msg_number_without_strip = whatsapp_msg_number_without_space.replace("-", "")
    #                         whatsapp_msg_number_without_code = whatsapp_msg_number_without_strip.replace(
    #                             '+' + str(partner_id.country_id.phone_code), "")
    #                         # phone_exists_url = param.get('whatsapp_endpoint') + '/checkPhone?token=' + param.get(
    #                         #     'whatsapp_token') + '&phone=' + str(
    #                         #     partner_id.country_id.phone_code) + "" + whatsapp_msg_number_without_code
    #                         # phone_exists_response = requests.get(phone_exists_url)
    #                         # json_response_phone_exists = json.loads(phone_exists_response.text)
    #                         # phone_exists_url = whatsapp_endpoint + '/check/' + whatsapp_instance + '/' + whatsapp_token
    #                         # phone_exists_response = requests.get(url, data=json.dumps({'phone': str(res_partner_id.country_id.phone_code) + whatsapp_msg_number_without_code}), headers={'Content-Type': 'application/json'})
    #                         # json_response_phone_exists = json.loads(phone_exists_response.text)['result']
    #                         # if (phone_exists_response.status_code == 200 or phone_exists_response.status_code == 201) and \
    #                         #         json_response_phone_exists['result'] == 'exists':
    #                         _logger.info("\nPartner phone exists")
    #                         # url = param.get('whatsapp_endpoint') + '/sendMessage?token=' + param.get('whatsapp_token')
    #                         # headers = {
    #                         #     "Content-Type": "application/json",
    #                         # }
    #                         url = whatsapp_endpoint + '/post'
    #                         headers = {"Content-Type": "application/json"}
    #                         html_to_plain_text = self.custom_html2plaintext(kwargs.get('body'))
    #                         if kwargs.get('email_from'):
    #                             if '<' in kwargs.get('email_from') and '>' in kwargs.get('email_from'):
    #                                 tmp_dict = {
    #                                     'params' : {
    #                                         "phone": str(
    #                                             partner_id.country_id.phone_code) + "" + whatsapp_msg_number_without_code,
    #                                         "body": self.convert_email_from_to_name(kwargs.get('email_from')) + '' + str(
    #                                             self.id) + ': ' + html_to_plain_text,   
    #                                         'instance': whatsapp_instance,
    #                                         'key': whatsapp_token,
    #                                         'method': 'sendMessage',
    #                                     }
    #                                 }
    #                             else:
    #                                 tmp_dict = {
    #                                     'params' : {
    #                                         "phone": str(
    #                                             partner_id.country_id.phone_code) + "" + whatsapp_msg_number_without_code,
    #                                         "body": kwargs.get('email_from') + '' + str(self.id) + ': ' + html_to_plain_text,   
    #                                         'instance': whatsapp_instance,
    #                                         'key': whatsapp_token,
    #                                         'method': 'sendMessage',
    #                                     }
    #                                 }
    #                         else:
    #                             tmp_dict = {
    #                                 'params' : {
    #                                     "phone": str(
    #                                         partner_id.country_id.phone_code) + "" + whatsapp_msg_number_without_code,
    #                                     "body": html_to_plain_text,   
    #                                     'instance': whatsapp_instance,
    #                                     'key': whatsapp_token,
    #                                     'method': 'sendMessage',
    #                                     }
    #                             }
    #                         response = requests.post(url, json.dumps(tmp_dict), headers=headers)
    #                         if response.status_code == 201 or response.status_code == 200:
    #                             _logger.info("\nSend Message successfully")
    #                             response_dict = response.json()
    #                             #message_id.with_context({'from_odoobot': True}).write({'whatsapp_message_id': response_dict.get('id')})
    #                         # else:
    #                         #     invalid_whatsapp_number_partner.append(partner_id.name)
    #                     else:
    #                         no_phone_partners.append(partner_id.name)
    #                 else:
    #                     raise UserError(_('bPlease authorize your mobile number with chat api'))

    #     if len(invalid_whatsapp_number_partner) >= 1:
    #         raise UserError(
    #             _('Please add valid whatsapp number for %s customer') % ', '.join(invalid_whatsapp_number_partner))
