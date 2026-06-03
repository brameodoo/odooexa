# -*- coding: utf-8 -*-
import secrets


def post_init_hook(env):
    """Create portal tokens for existing active employees after install.

    Field defaults only apply to newly-created employees. Most SGS custodians
    already exist in HR before this module is installed, so generate missing
    tokens once the module fields are available.
    """
    employees = env['hr.employee'].sudo().search([
        ('active', '=', True),
        ('portal_token', '=', False),
    ])
    for employee in employees:
        employee.portal_token = secrets.token_urlsafe(24)
