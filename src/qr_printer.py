# src/qr_printer.py
import qrcode

def print_qr_terminal(data: str) -> None:
    qr = qrcode.QRCode(
        version=1,  # 控制二维码的大小
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=8,  # 控制二维码字符的大小
        border=1,  # 边框大小
    )

    qr.add_data(data)
    qr.make(fit=True)
    qr.print_ascii(invert=True)