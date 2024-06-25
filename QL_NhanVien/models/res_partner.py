from odoo import models, fields, api

class ResPartner(models.Model):
    _inherit = 'res.partner'

    signup_expiration = fields.Datetime(groups='QL_NhanVien.group_ql_nhanvien_manager')
    signup_token = fields.Char(groups='QL_NhanVien.group_ql_nhanvien_manager')
    signup_type = fields.Char(groups='QL_NhanVien.group_ql_nhanvien_manager')
