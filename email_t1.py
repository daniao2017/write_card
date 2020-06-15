#!/usr/bin/python
# -*- coding: UTF-8 -*-

import smtplib
import os
from aip import AipSpeech
from email.mime.text import MIMEText
from email.header import Header
from email.mime.multipart import MIMEMultipart 


def baidu_tts(name):
    APP_ID = xxxxxx
    API_KEY = xxxxx
    SECRET_KEY = xxxx
    test = "祝{0}同学前程似锦,平安喜乐".format(name)
    client = AipSpeech(APP_ID, API_KEY, SECRET_KEY)
    base_path = os.path.dirname(__file__)  # 当前文件所在路径
    tts_path = os.path.join(base_path, "static/music/")
    tts_path = tts_path + "baidu_tts.mp3"
    result  = client.synthesis(str(test), 'zh', 1, {
    'vol': 5,"per":1})
    # 识别正确返回语音二进制 错误则返回dict 参照下面错误码
    if not isinstance(result, dict):
        with open(tts_path, 'wb') as f:
            f.write(result)


def email_callback(name,email_name):
    name = str(name)
    email_name = str(email_name)
    #合成祝福语
    baidu_tts(name)
    # 第三方 SMTP 服务
    mail_host="smtp.qq.com"  #设置服务器
    mail_user="2868108923@qq.com"    #用户名
    mail_pass="xxxx"   #口令 
    sender = '2868108923@qq.com' 
    receivers = [email_name]  # 接收邮件，可设置为你的QQ邮箱或者其他邮箱
    subject = '来自母校的明信片'
    message = MIMEMultipart()    
    #message = MIMEText(message_fix, 'plain', 'utf-8')
    message['Subject'] = Header(subject, 'utf-8')
    message['From'] = Header("邮箱", 'utf-8') #发件人
    message['To'] =  Header(name, 'utf-8')
     # 注意：没有的文件夹一定要先创建，不然会提示没有该路径
    base_path = os.path.dirname(__file__)  # 当前文件所在路径
    html_file =  os.path.join(base_path, "templates/","email_send.html")  
    sendFile = open(html_file,"rb").read()
    message.attach(MIMEText(open(html_file,"rb").read(), 'html', 'utf-8'))
    # 构造附件1,明信片前景
    att_file1 = os.path.join(base_path, "static/images/results","test.jpg")
    sendFile = open(att_file1,"rb").read()
    att1 = MIMEText(sendFile, 'base64', 'utf-8') 
    att1['Content-Type'] = 'application/octet-stream' 
    att1['Content-Disposition'] = 'attachment; filename="head_image.jpg"' 
    message.attach(att1)
    # 构造附件2,明信片后景
    att_file2 = os.path.join(base_path, "static/images/results","huidu_target2.png")
    sendFile = open(att_file2,"rb").read()
    att2 = MIMEText(sendFile, 'base64', 'utf-8') 
    att2['Content-Type'] = 'application/octet-stream' 
    att2['Content-Disposition'] = 'attachment; filename="back_image.jpg"' 
    message.attach(att2)
    # 构造附件3,祝福语
    att_file3 = os.path.join(base_path, "static/music","baidu_tts.mp3")
    sendFile = open(att_file3,"rb").read()
    att3 = MIMEText(sendFile, 'base64', 'utf-8') 
    att3['Content-Type'] = 'application/octet-stream' 
    att3['Content-Disposition'] = 'attachment; filename="baidu_tts.mp3"' 
    message.attach(att3)
    try:
        smtpObj = smtplib.SMTP() 
        smtpObj.connect(mail_host, 465)    # 25 为 SMTP 端口号
        smtpObj.login(mail_user,mail_pass)  
        smtpObj.sendmail(sender, receivers, message.as_string())
        print ("邮件发送成功")
    except smtplib.SMTPException:
        print ("Error: 无法发送邮件")
if __name__ == "__main__":
    name = "小刘"
    email_name = "2868108923@qq.com"
    email_callback(name,email_name)
