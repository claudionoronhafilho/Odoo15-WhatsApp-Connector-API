# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools, SUPERUSER_ID, _

class ApiRestPath(models.Model):
    _inherit = 'api.rest.path'

    livechat_active = fields.Boolean('Is livechat?', help='Livechat session is active until visitor leave the conversation.')
    channel_line = fields.One2many('mail.channel', 'path_id', string="Channels") 
