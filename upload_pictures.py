# coding:utf-8

from flask import Flask, render_template, request, redirect, url_for, make_response, jsonify
from werkzeug.utils import secure_filename
import os
import cv2
import time
import numpy as np
from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont
import requests
import json
import base64

from datetime import timedelta

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

        return render_template('upload_ok.html', val1=time.time())
    return render_template('upload.html')


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
if __name__ == '__main__':
    # app.debug = True
    app.run(host='0.0.0.0', port=520, debug=True)
