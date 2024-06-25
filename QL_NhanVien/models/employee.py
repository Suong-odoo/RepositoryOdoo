from odoo import models, fields, api
import qrcode
from io import BytesIO
import base64
from odoo.exceptions import ValidationError

class Employee(models.Model):
    _name = 'ql_nhanvien.employee'
    _description = 'Nhân viên'
    _sql_constraints = [
        ('unique_qr_code', 'unique(qr_code)', 'Mã QR phải là duy nhất!'),
        ('unique_card_number', 'unique(card_number)', 'Mã số thẻ phải là duy nhất!'),
    ]

    name = fields.Char(string="Tên nhân viên", required=True, track_visibility='onchange')
    image = fields.Binary(string='Image', attachment=True)
    employee_id = fields.Char(string="Mã nhân viên")
    department_id = fields.Many2one('ql_nhanvien.department', string="Phòng ban", ondelete="cascade")
    role_ids = fields.Many2many('ql_nhanvien.role', string="Vị trí")
    work_mobile = fields.Char(string='Work Mobile')
    work_email = fields.Char(string='Work Email', required=True)  # Bắt buộc để liên kết với người dùng
    gender = fields.Selection([('male', 'Nam'), ('female', 'Nữ')], string='Gender', default='male')
    country = fields.Char(string='Country')
    domicile = fields.Char(string='Domicile')
    day_of_birth = fields.Datetime(string='Day of Birth')
    user_id = fields.Many2one('res.users', string='User', ondelete='cascade', required=True)
    work_location = fields.Char(string='Địa điểm làm việc')
    work_schedule = fields.Selection([
        ('56 hours/week', '56 giờ/tuần'),
        ('48 hours/week', '48 giờ/tuần'),
        ('40 hours/week', '40 giờ/tuần'),
    ], string='Lịch làm việc')

    home_address = fields.Char(string='Địa chỉ Nhà')
    personal_email = fields.Char(string='Email Riêng')
    bank_account_number = fields.Char(string='STK Ngân hàng')
    education_level = fields.Selection([
        ('university', 'Đại học'),
        ('college', 'Cao đẳng'),
        ('masters', 'Thạc sĩ'),
        ('other', 'Khác')
    ], string='Cấp độ chứng nhận')

    degree = fields.Binary('Bằng cấp', attachment=True)
    certificate = fields.Binary('Chứng chỉ', attachment=True)
    study_field = fields.Char(string='Lĩnh vực nghiên cứu')
    school = fields.Char(string='Trường học')
    visa_number = fields.Char(string='Số Visa')
    work_permit_number = fields.Char(string='Số Giấy phép LĐ')
    visa_expire_date = fields.Date(string='Ngày hết Hạn Visa')
    work_permit_expire_date = fields.Date(string='Ngày hết hạn giấy phép LĐ')
    work_permit_attachment = fields.Binary(string='Giấy phép LĐ')
    wage = fields.Selection([
        ('low', 'Mức thấp: 3 triệu - 5 triệu'),
        ('high', 'Mức cao: 5 triệu - 20 triệu')
    ], string='Mức lương')

    employee_type = fields.Selection([
        ('permanent', 'Nhân viên'),
        ('contract', 'Thực tập'),
        ('temporary', 'Thử việc')
    ], string='Kiểu Nhân viên')

    @api.constrains('work_mobile')
    def _check_work_mobile(self):
        for record in self:
            if record.work_mobile and (len(record.work_mobile) >= 10 or not record.work_mobile.isdigit()):
                raise ValidationError("Số điện thoại di động phải có đúng 10 chữ số.")

    qr_code = fields.Char(string='Mã QR')
    card_number = fields.Char(string='Mã số Thẻ')
    qr_code_image = fields.Binary("QR Code", attachment=True, compute='_compute_qr_code')
    qr_code_created = fields.Boolean(string="QR Code Created", default=False)

    @api.model
    def create(self, vals):
        if 'work_email' in vals:
            user = self.env['res.users'].search([('login', '=', vals['work_email'])], limit=1)
            if user:
                vals['user_id'] = user.id
            else:
                user = self.env['res.users'].create({
                    'name': vals.get('name'),
                    'login': vals['work_email'],
                    'email': vals['work_email'],
                    'groups_id': [(6, 0, [self.env.ref('QL_NhanVien.group_ql_nhanvien_user').id])]
                })
                vals['user_id'] = user.id
        else:
            raise ValidationError("Vui lòng cung cấp email công việc để liên kết với người dùng.")

        # Tự động tạo mã số thẻ nếu chưa có
        if 'card_number' not in vals or not vals['card_number']:
            vals['card_number'] = self.env['ir.sequence'].next_by_code('ql_nhanvien.employee.card_number') or 'New'

        # Kiểm tra trùng lặp mã QR và mã số thẻ
        if 'qr_code' in vals and vals['qr_code']:
            if self.env['ql_nhanvien.employee'].search([('qr_code', '=', vals['qr_code'])]):
                raise ValidationError("Mã QR đã tồn tại.")
        if 'card_number' in vals and vals['card_number']:
            if self.env['ql_nhanvien.employee'].search([('card_number', '=', vals['card_number'])]):
                raise ValidationError("Mã số thẻ đã tồn tại.")

        return super(Employee, self).create(vals)

    def write(self, vals):
        if 'work_email' in vals:
            user = self.env['res.users'].search([('login', '=', vals['work_email'])], limit=1)
            if user:
                vals['user_id'] = user.id
            else:
                user = self.env['res.users'].create({
                    'name': self.name,
                    'login': vals['work_email'],
                    'email': vals['work_email'],
                    'groups_id': [(6, 0, [self.env.ref('QL_NhanVien.group_ql_nhanvien_user').id])]
                })
                vals['user_id'] = user.id

        # Kiểm tra trùng lặp mã QR và mã số thẻ
        if 'qr_code' in vals and vals['qr_code']:
            if self.env['ql_nhanvien.employee'].search([('qr_code', '=', vals['qr_code']), ('id', '!=', self.id)]):
                raise ValidationError("Mã QR đã tồn tại.")
        if 'card_number' in vals and vals['card_number']:
            if self.env['ql_nhanvien.employee'].search([('card_number', '=', vals['card_number']), ('id', '!=', self.id)]):
                raise ValidationError("Mã số thẻ đã tồn tại.")

        return super(Employee, self).write(vals)

    @api.depends('employee_id', 'qr_code', 'card_number')
    def _compute_qr_code(self):
        for record in self:
            if record.employee_id and record.qr_code and record.card_number:
                qr = qrcode.QRCode(
                    version=1,
                    error_correction=qrcode.constants.ERROR_CORRECT_L,
                    box_size=10,
                    border=4,
                )
                qr_data = (
                    f"Mã NV: {record.employee_id}\n"
                    f"Họ và tên: {record.name}\n"
                    # f"HÌnh ảnh: {record.image}\n"
                    f"Mã QR code: {record.qr_code}\n"
                    f"Số thẻ: {record.card_number}\n"
                    f"Phòng ban: {record.department_id.name if record.department_id else 'N/A'}\n"
                    f"Vị trí: {', '.join(record.role_ids.mapped('name')) if record.role_ids else 'N/A'}"
                )
                qr.add_data(qr_data)
                qr.make(fit=True)

                img = qr.make_image(fill='black', back_color='white')
                temp = BytesIO()
                img.save(temp, format="PNG")
                qr_image = base64.b64encode(temp.getvalue()).decode('utf-8')
                temp.close()

                record.qr_code_image = qr_image
                record.qr_code_created = True
            else:
                record.qr_code_image = False
                record.qr_code_created = False

    def action_create_something(self):
        self.ensure_one()
        self._compute_qr_code()
        return {
            'effect': {
                'fadeout': 'slow',
                'message': 'Tạo thành công',
                'type': 'rainbow_man',
            }
        }

    def action_edit_something(self):
        return {
            'effect': {
                'fadeout': 'slow',
                'message': 'Chỉnh sửa thành công',
                'type': 'rainbow_man',
            }
        }

    def action_download_qr(self):
        self.ensure_one()
        qr_image = base64.b64decode(self.qr_code_image)
        qr_filename = f"{self.employee_id}_qr_code.png"
        attachment = self.env['ir.attachment'].create({
            'name': qr_filename,
            'type': 'binary',
            'datas': self.qr_code_image,
            'store_fname': qr_filename,
            'res_model': self._name,
            'res_id': self.id,
            'mimetype': 'image/png'
        })
        url = f'/web/content/{attachment.id}?download=true'
        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'self',
        }

    attendance_ids = fields.One2many('ql_nhanvien.attendance', 'employee_id', string='Chấm công')

    def action_check_in(self):
        check_in_time = fields.Datetime.now()
        attendance = self.env['ql_nhanvien.attendance'].create({
            'employee_id': self.id,
            'check_in': check_in_time,
        })
        if attendance.status == 'late':
            minutes_late = attendance.late_minutes
            message = f'Bạn đã đến trễ {minutes_late} phút.'
        else:
            message = 'Bạn đã chấm công đúng giờ.'
        return {
            'effect': {
                'fadeout': 'slow',
                'message': message,
                'type': 'rainbow_man',
            }
        }

    def action_check_out(self):
        attendance = self.env['ql_nhanvien.attendance'].search([('employee_id', '=', self.id)], order='check_in desc', limit=1)
        if attendance and not attendance.check_out:
            check_out_time = fields.Datetime.now()
            attendance.write({'check_out': check_out_time})
            return {
                'effect': {
                    'fadeout': 'slow',
                    'message': f'Bạn đã chấm công ra lúc {check_out_time.strftime("%H:%M:%S")}',
                    'type': 'rainbow_man',
                }
            }
        else:
            return {
                'warning': {
                    'title': "Không tìm thấy bản ghi chấm công",
                    'message': "Bạn phải chấm công vào trước khi chấm công ra."
                }
            }
