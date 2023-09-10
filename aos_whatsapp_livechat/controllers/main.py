
import json
import random
import requests
from odoo import http
from odoo.http import request
from odoo import api, Command, fields, models, modules, _, http, SUPERUSER_ID
# from odoo.addons.mail.controllers import mail
# from odoo.addons.aos_whatsapp_bot.controllers import webhook
# from odoo.addons.muk_rest import validators, tools

class PartnerController(http.Controller):

    @http.route('/webhook/test', type="json", auth='public', methods=['POST'])
    def some_html(self, **kw):
        return {
            'success': True,
            'status': 'OK',
            'code': 200
        }
    
    @http.route('/webhook/partner', type="json", auth='public', methods=['GET'])
    def webhook_partner(self, **kw):
        get_param = request.env['ir.config_parameter'].sudo().get_param('webhook.url')
        #print ('==s==',get_param)
        return {
            'success': True,
            'status': 'OK',
            'webhook': get_param,
            'code': 200
        }

    def _get_available_users(self):
        """ get available user of a given channel
            :retuns : return the res.users having their im_status online
        """
        #request.ensure_one()
        #print ('===_get_available_users==',request.env['im_livechat.channel'].sudo().search([], limit=1).user_ids)
        return request.env['im_livechat.channel'].sudo().search([], limit=1).user_ids.filtered(lambda user: user.im_status == 'online')

    def _get_whatsapp_mail_channel_vals(self, senderkeyhash, anonymous_name, operator, user_id=None, country_id=None):
        # partner to add to the mail.channel
        # senderkeyhash = self.senderkeyhash
        im_livechat_channel = request.env['im_livechat.channel'].search([], limit=1)
        operator_partner_id = operator.partner_id.id
        channel_partner_to_add = [Command.create({'partner_id': operator_partner_id, 'is_pinned': False})]
        visitor_user = False
        if user_id:
            visitor_user = request.env['res.users'].browse(user_id)
            if visitor_user and visitor_user.active and visitor_user != operator:  # valid session user (not public)
                channel_partner_to_add.append(Command.create({'partner_id': visitor_user.partner_id.id}))
        #print ('===channel_partner_to_add==',anonymous_name)
        return {
            'senderkeyhash': senderkeyhash,
            'channel_last_seen_partner_ids': channel_partner_to_add,
            'livechat_active': True,
            'livechat_operator_id': operator_partner_id,
            'livechat_channel_id': im_livechat_channel.id,
            'anonymous_name': False if user_id else anonymous_name,
            'country_id': country_id,
            'channel_type': 'livechat',
            'name': ' '.join([visitor_user.display_name if visitor_user else anonymous_name, operator.livechat_username if operator.livechat_username else operator.name]),
            'public': 'private',
        }
    
    def _get_random_operator(self):
        """ Return a random operator from the available users of the channel that have the lowest number of active livechats.
        A livechat is considered 'active' if it has at least one message within the 30 minutes.

        (Some annoying conversions have to be made on the fly because this model holds 'res.users' as available operators
        and the mail_channel model stores the partner_id of the randomly selected operator)

        :return : user
        :rtype : res.users
        """
        operators = self._get_available_users()
        if len(operators) == 0:
            return False

        request.env.cr.execute("""SELECT COUNT(DISTINCT c.id), c.livechat_operator_id
            FROM mail_channel c
            LEFT OUTER JOIN mail_message m ON c.id = m.res_id AND m.model = 'mail.channel'
            WHERE c.channel_type = 'livechat'
            AND c.livechat_operator_id in %s
            AND m.create_date > ((now() at time zone 'UTC') - interval '30 minutes')
            GROUP BY c.livechat_operator_id
            ORDER BY COUNT(DISTINCT c.id) asc""", (tuple(operators.mapped('partner_id').ids),))
        active_channels = request.env.cr.dictfetchall()

        # If inactive operator(s), return one of them
        active_channel_operator_ids = [active_channel['livechat_operator_id'] for active_channel in active_channels]
        inactive_operators = [operator for operator in operators if operator.partner_id.id not in active_channel_operator_ids]
        if inactive_operators:
            return random.choice(inactive_operators)

        # If no inactive operator, active_channels is not empty as len(operators) > 0 (see above).
        # Get the less active operator using the active_channels first element's count (since they are sorted 'ascending')
        lowest_number_of_conversations = active_channels[0]['count']
        less_active_operator = random.choice([
            active_channel['livechat_operator_id'] for active_channel in active_channels
            if active_channel['count'] == lowest_number_of_conversations])

        # convert the selected 'partner_id' to its corresponding res.users
        return next(operator for operator in operators if operator.partner_id.id == less_active_operator)

    def _whatsapp_mail_channel(self, senderkeyhash, anonymous_name, previous_operator_id=None, user_id=None, country_id=None):
        """ Return a mail.channel given a livechat channel. It creates one with a connected operator, or return false otherwise
            :param anonymous_name : the name of the anonymous person of the channel
            :param previous_operator_id : partner_id.id of the previous operator that this visitor had in the past
            :param user_id : the id of the logged in visitor, if any
            :param country_code : the country of the anonymous person of the channel
            :type anonymous_name : str
            :return : channel header
            :rtype : dict

            If this visitor already had an operator within the last 7 days (information stored with the 'im_livechat_previous_operator_pid' cookie),
            the system will first try to assign that operator if he's available (to improve user experience).
        """
        #print ('===_whatsapp_mail_channel===',anonymous_name, previous_operator_id, user_id, country_id)
        #request.ensure_one()
        operator = False
        if previous_operator_id:
            available_users = self._get_available_users()
            # previous_operator_id is the partner_id of the previous operator, need to convert to user
            if previous_operator_id in available_users.mapped('partner_id').ids:
                operator = next(available_user for available_user in available_users if available_user.partner_id.id == previous_operator_id)
        if not operator:
            operator = self._get_random_operator()
        if not operator:
            # no one available
            return False

        # create the session, and add the link with the given channel
        mail_channel_vals = self._get_whatsapp_mail_channel_vals(senderkeyhash, anonymous_name, operator, user_id=user_id, country_id=country_id)
        #print ('===mail_channel_vals==whlive=',anonymous_name, operator, user_id, country_id, mail_channel_vals)
        mail_channel = request.env["mail.channel"].with_context(mail_create_nosubscribe=False).sudo().create(mail_channel_vals)
        mail_channel._broadcast([operator.partner_id.id])
        #print ('=channel_info=',mail_channel.sudo())
        #return mail_channel.sudo().channel_info()[0]
        return mail_channel.sudo()
        
    @http.route('/webhook/livechat', auth="none", type='json', methods=['POST'], csrf=False)
    def whatsapp_channel(self, **kwargs):
        #print ('===/whatsapp_livechat/get_session=11==',request.env.user)
        #print ('==create_rest_api_partner_aos=',kwargs)
        if not kwargs:
            return request.make_response(
                data=json.dumps({'error': 'No Data'}),
                headers=[('Content-Type', 'application/json')]
            )
        uuid = kwargs.get('uuid')
        api_key = kwargs.get('x-api-key')
        sender = kwargs.get('sender')
        message = kwargs.get('message')
        senderkeyhash = kwargs.get('senderkeyhash')
        recipientkeyhash = kwargs.get('recipientkeyhash')
        # print ('===/whatsapp_livechat/uuid==',uuid)
        # print ('===/whatsapp_livechat/api_key==',api_key)
        # print ('===/whatsapp_livechat/sender==',sender)
        # print ('===/whatsapp_livechat/message==',message)
        # print ('===/whatsapp_livechat/senderkeyhash==',senderkeyhash)
        PublicUser = request.env.user
        if not request.env.user:
            PublicUser = request.env['res.users'].sudo().search([('active','=',False),('login','=','public')], limit=1)
            request.env.user = PublicUser
        Partner = request.env['res.partner'].sudo().search([('whatsapp','=',sender)], limit=1)
        #print ('===/whatsapp_livechat/get_session=22==',request.env.user)
        anonymous_name = 'Visitor'
        if Partner:
            anonymous_name = Partner.name
        user_id = None
        country_id = None
        previous_operator_id = None
        anonymous_name = Partner.name
        #user_id = PublicUser.id
        # if Partner:
        #     Partner = PublicUser.partner_id or False
        # if the user is identifiy (eg: portal user on the frontend), don't use the anonymous name. The user will be added to session.
        if request.env.user:
            user_id = request.env.user.id
            country_id = request.env.user.country_id.id
        else:
            # if geoip, add the country name to the anonymous name
            if request.session.geoip:
                # get the country of the anonymous person, if any
                country_code = request.session.geoip.get('country_code', "")
                country = request.env['res.country'].sudo().search([('code', '=', country_code)], limit=1) if country_code else None
                if country:
                    anonymous_name = "%s (%s)" % (anonymous_name, country.name)
                    country_id = country.id

        if previous_operator_id:
            previous_operator_id = int(previous_operator_id)
        #channel_id = False
        MailChannel = request.env['mail.channel'].sudo().search([('uuid','=',uuid),('senderkeyhash', '=', senderkeyhash),('livechat_active','=',True)], limit=1)
        #print ('==ActiveMailChannel===',MailChannel)
        #previous_operator_id = MailChannel.livechat_operator_id
        previous_operator_id = self._get_available_users().mapped('partner_id') and self._get_available_users().mapped('partner_id')[0].id
        
        #Partner = request.env['res.partner'].sudo().search([('whatsapp','=',sender)], limit=1)
        # anonymous_name = Partner.name
        #user_id = PublicUser.id
        if not Partner:
            Partner = PublicUser.partner_id or False
        #print ('=anonymous_name==',anonymous_name)
        if not MailChannel:
            MailChannel = self._whatsapp_mail_channel(senderkeyhash, anonymous_name, previous_operator_id, user_id, country_id)
            if not MailChannel:
                response_data = {
                    'error': 'Error',
                    'user_id': False,
                }
                #print ('==response_data==',response_data)
                return response_data
            uuid = MailChannel.uuid
        #print ('==PublicUser===',Partner,MailChannel)
        MailChannel.message_post(
            whatsapp_numbers=sender,
            body=message,
            message_type='notification',
            author_id=Partner.id
        )
        response_data = {
            'uuid': MailChannel.uuid,
            'user_id': user_id,
        }
        return response_data#json.dumps(response_data)
        # return request.make_response(
        #     data=json.dumps(response_data),
        #     headers=[('Content-Type', 'application/json')]
        # ) 
