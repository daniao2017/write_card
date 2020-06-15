#!/usr/bin/python
# coding:utf-8

from flask import Flask, render_template, request, redirect, url_for, make_response, jsonify
from werkzeug.utils import secure_filename
import os
import time
import requests
import json
import base64

from datetime import timedelta
#百度tts
from aip import AipSpeech
#发送邮件
import smtplib
from email.mime.text import MIMEText
from email.header import Header
from email.mime.multipart import MIMEMultipart 
#图像处理
import cv2
import numpy as np
from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont

# 设置允许的文件格式
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'JPG', 'PNG', 'bmp'])


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS


app = Flask(__name__)
# 设置静态文件缓存过期时间
app.send_file_max_age_default = timedelta(seconds=1)


@app.route('/upload', methods=['POST', 'GET'])  # 添加路由
def upload():
    if request.method == 'POST':
        f = request.files['file']
        username = request.form.get('name')
        email_name = request.form.get('email_name')
        if not (f and allowed_file(f.filename)):
            return jsonify({"error": 1001, "msg": "请检查上传的图片类型，仅限于png、PNG、jpg、JPG、bmp"})
        basepath = os.path.dirname(__file__)  # 当前文件所在路径
        upload_path = os.path.join(basepath, 'static/images/source',
                                   secure_filename(f.filename))  # 注意：没有的文件夹一定要先创建，不然会提示没有该路径
        f.save(upload_path)

        # 使用Opencv转换一下图片格式和名称
        img = cv2.imread(upload_path)
        cv2.imwrite(os.path.join(basepath, 'static/images/source', 'test.jpg'), img)
        convert(basepath, upload_path)
        time.sleep(3)
        combination_pic()
        add_text_huidu(username,basepath)
        email_name = str(email_name)
        email_callback(username,email_name)
        return render_template('upload_ok.html', val1=time.time())
    return render_template('upload.html')

@app.route('/note', methods=['POST', 'GET'])  # 添加路由
def note():
    return render_template('note.html')

def convert(basepath, upload_path):
    file_list = [upload_path]
    files = [("image", (open(item, "rb"))) for item in file_list]
    # 指定图片分割方法为deeplabv3p_xception65_humanseg并发送post请求
    url = "http://127.0.0.1:8866/predict/image/deeplabv3p_xception65_humanseg"
    r = requests.post(url=url, files=files)

    results = eval(r.json()["results"])
    for item in results:
        mypath = os.path.join(basepath, 'static/images/target', 'test.jpg')
        print('*' * 100)
        print(item["processed"].split("/")[-1].split("/")[-1])
        print('*' * 100)
        with open(mypath, "wb") as fp:
            fp.write(base64.b64decode(item["base64"].split(',')[-1]))
            item.pop("base64")
    print(json.dumps(results, indent=4, ensure_ascii=False))
def blend_images(fore_image, base_image, ratio, pos=None, align_bottom=True):
    """
    将抠出的人物图像换背景
    fore_image: 前景图片，抠出的人物图片
    base_image: 背景图片
    ratio: 调整前景的比例
    pos: 前景放在背景的位置的，格式为左上角坐标
    align_bottom: 默认使用底边对齐
    """
    
    bg_img = cv2.imread(base_image)  # read background image
    fg_img = cv2.imread(fore_image)  # read foreground image
    #bg_img = bg_img.resize((617,283))
    height_fg, width_fg, _ = fg_img.shape  # get height and width of foreground image
    height_bg, width_bg, _ = bg_img.shape  # get height and width of background image
    if ratio > (height_bg / height_fg): 
        print('ratio is too large, use maximum ratio {(height_bg / height_fg): .2}')
        ratio =round((height_bg / height_fg), 1)
    if ratio <  0.1:
        print('ratio < 0.1, use minimum ratio 0.1' )
        ratio  = 0.1
    # if no pos arg input, use this as default
    if not pos:
        pos = (height_bg - int(ratio*height_fg),  width_bg // 4)#底边对齐：hb-hf为纵坐标，//整除,背景图的1//4宽为横坐标
    elif align_bottom:
        pos = (height_bg - int(ratio*height_fg), pos[1])

    roi = bg_img[pos[0]: pos[0] + int(height_fg * ratio), pos[1] : pos[1]+int(width_fg*ratio)]#背景图片编辑
    basepath1 = os.path.dirname(__file__)  # 当前文件所在路径
    roi_path = os.path.join(basepath1, 'static/images/source', 'roi.jpg')
    cv2.imwrite(roi_path, roi)
    base_image = Image.open(roi_path).convert('RGB')
    fore_image = Image.open(fore_image).resize(base_image.size)
    # 图片加权合成
    scope_map = np.array(fore_image)[:,:,-1] / 255
    scope_map = scope_map[:,:,np.newaxis]
    scope_map = np.repeat(scope_map, repeats=3, axis=2)
    res_image = np.multiply(scope_map, np.array(fore_image)[:,:,:3]) + np.multiply((1-scope_map), np.array(base_image))
    
    bg_img[pos[0]: pos[0] + roi.shape[0], pos[1] : pos[1]+roi.shape[1]] = np.uint8(res_image)[:, : , ::-1]
    return bg_img

def combination_pic():
    basepath2 = os.path.dirname(__file__)  # 当前文件所在路径
    base_path = os.path.join(basepath2, 'static/images/results', 'base_pic.jpg')
    forse_path = os.path.join(basepath2, 'static/images/target', 'test.jpg')
    results_path =  os.path.join(basepath2, 'static/images/results', 'test.jpg')
    img  = blend_images(forse_path, base_path, 0.2,pos=(20,80))
    cv2.imwrite(results_path,img)

def add_text_huidu(username,basepath):
    #设置所使用的字体
    fontpath = os.path.join(basepath, 'static/font', 'simhei.ttf')
    font1 = ImageFont.truetype(fontpath, 20)
    yourname=str(username)
    #打开图片
    imgpath = os.path.join(basepath, 'static/images/results', 'huidu_target.png')
    text1 = "祝" + yourname + "同学，"
    text2 = "前程似锦"
    im1 = Image.open(imgpath)  
    #画图
    draw = ImageDraw.Draw(im1)
    # 祝福语
    draw.text(xy=(400,30),text=text1,font=font1,)    
    draw.text(xy=(450,60),text=text2,font=font1,)
    saveimg = os.path.join(basepath, 'static/images/results', 'huidu_target2.png')
    im1.save(saveimg)

def baidu_tts(tts_name):
    tts_name = str(tts_name)
    APP_ID = "10778068"
    API_KEY = "90ynbXXfuNGoNMGf5Fqx9nSI"
    SECRET_KEY = "9f6bae32625ee9ad3ae33dd64b6f79b1"
    test = "相逢又告别，归帆又离岸，是往日欢乐的终结，未来幸福的开端。祝{0}同学前程似锦,平安喜乐".format(tts_name)
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
    time.sleep(3)
    # 第三方 SMTP 服务
    mail_host="smtp.qq.com"  #设置服务器
    mail_user="xxxx"    #用户名
    mail_pass="xxxxx"   #口令 
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
        smtpObj.connect(mail_host, 25)    # 25 为 SMTP 端口号
        smtpObj.login(mail_user,mail_pass)  
        smtpObj.sendmail(sender, receivers, message.as_string())
        print ("邮件发送成功")
    except smtplib.SMTPException:
        print ("Error: 无法发送邮件")
        error_index = -1
if __name__ == '__main__':
    # app.debug = True
    app.run(host='0.0.0.0', port=520, debug=True)
