from enum import Enum, auto
from qrcode import QRCode, constants
from PIL import Image, ImageDraw, ImageFont
import textwrap
import requests
import json
import yaml

class LabelContent(Enum):
    TEXT_ONLY = auto()
    QRCODE_ONLY = auto()
    TEXT_QRCODE = auto()
    IMAGE = auto()
    PARTSBOX_PART = auto()
    PARTSBOX_STORAGE = auto()


class LabelOrientation(Enum):
    STANDARD = auto()
    ROTATED = auto()


class LabelType(Enum):
    ENDLESS_LABEL = auto()
    DIE_CUT_LABEL = auto()
    ROUND_DIE_CUT_LABEL = auto()


class TextAlign(Enum):
    LEFT = 'left'
    CENTER = 'center'
    RIGHT = 'right'


class SimpleLabel:
    qr_correction_mapping = {
        'L': constants.ERROR_CORRECT_L,
        'M': constants.ERROR_CORRECT_M,
        'Q': constants.ERROR_CORRECT_Q,
        'H': constants.ERROR_CORRECT_H
    }

    def __init__(
            self,
            width=0,
            height=0,
            label_content=LabelContent.TEXT_ONLY,
            label_orientation=LabelOrientation.STANDARD,
            label_company='',
            label_type=LabelType.ENDLESS_LABEL,
            label_margin=(0, 0, 0, 0),  # Left, Right, Top, Bottom
            fore_color=(0, 0, 0),  # Red, Green, Blue
            text='',
            text_align=TextAlign.CENTER,
            qr_size=10,
            qr_correction='L',
            image=None,
            font_path='',
            font_size=70,
            line_spacing=100,
            partsbox_user_url='',
            partsbox_api_url='',
            partsbox_api_key=''):
        self._width = width
        self._height = height
        self.label_content = label_content
        self.label_orientation = label_orientation
        self.label_company = label_company
        self.label_type = label_type
        self._label_margin = label_margin
        self._fore_color = fore_color
        self.text = text
        self._text_align = text_align
        self._qr_size = qr_size
        self.qr_correction = qr_correction
        self._image = image
        self._font_path = font_path
        self._font_size = font_size
        self._line_spacing = line_spacing
        self.partsbox_user_url = partsbox_user_url
        self.partsbox_api_url = partsbox_api_url
        self.partsbox_api_key = partsbox_api_key

    @property
    def label_content(self):
        return self._label_content

    @label_content.setter
    def label_content(self, value):
        self._label_content = value

    @property
    def text(self):
        return self._text

    @text.setter
    def text(self, value):
        self._text = value

    @property
    def qr_correction(self):
        for key, val in self.qr_correction_mapping:
            if val == self._qr_correction:
                return key

    @qr_correction.setter
    def qr_correction(self, value):
        self._qr_correction = self.qr_correction_mapping.get(
            value, constants.ERROR_CORRECT_L)

    @property
    def label_orientation(self):
        return self._label_orientation

    @label_orientation.setter
    def label_orientation(self, value):
        self._label_orientation = value

    @property
    def label_type(self):
        return self._label_type

    @label_type.setter
    def label_type(self, value):
        self._label_type = value

    
    def get_font_size(self, text, font, max_width=None, max_height=None):
        if max_width is None and max_height is None:
            raise ValueError('You need to pass max_width or max_height')
        font_size = 1
        text_size = self.get_text_size(font, font_size, text)
        if (max_width is not None and text_size[0] > max_width) or \
            (max_height is not None and text_size[1] > max_height):
            raise ValueError("Text can't be filled in only (%dpx, %dpx)" % \
                    text_size)
        while True:
            if (max_width is not None and text_size[0] >= max_width) or \
                (max_height is not None and text_size[1] >= max_height):
                return font_size - 1
            font_size += 1
            text_size = self.get_text_size(font, font_size, text)

    def write_text(self, img, xy, text, font_filename, font_size=11,
                    color=(0, 0, 0), max_width=None, max_height=None):
        x, y = xy
        if font_size == 'fill' and \
            (max_width is not None or max_height is not None):
            font_size = self.get_font_size(text, font_filename, max_width,
                                            max_height)
        text_size = self.get_text_size(font_filename, font_size, text)
        font = ImageFont.truetype(font_filename, font_size)
        if x == 'center':
            x = (self.size[0] - text_size[0]) / 2
        if y == 'center':
            y = (self.size[1] - text_size[1]) / 2
        ImageDraw.Draw(img).text((x, y), text, font=font, fill=color)
        return text_size

    def draw_line(self, img, coordinates):
        ImageDraw.Draw(img).line(coordinates, fill="black")

    def get_text_size(self, font_filename, font_size, text):
        font = ImageFont.truetype(font_filename, font_size)
        return font.getsize(text)

    def write_text_box(self, img, xy, text, box_width, font_filename,
                        font_size=11, color=(0, 0, 0), place='left',
                        justify_last_line=False, position='top',
                        line_spacing=1.0, box_height=None):
        x, y = xy

        while box_height is not None:
            # This splits text and creates a multi-lin
            lines = []
            line = []
            words = text.split()
            for word in words:
                new_line = ' '.join(line + [word])
                size = self.get_text_size(font_filename, font_size, new_line)
                text_height = size[1] * line_spacing
                last_line_bleed = text_height - size[1]
                if size[0] <= box_width:
                    line.append(word)
                else:
                    lines.append(line)
                    line = [word]
            if line:
                lines.append(line)
            lines = [' '.join(line) for line in lines if line]
            
            if position == 'middle':
                height = (self.size[1] - len(lines)*text_height + last_line_bleed)/2
                height -= text_height # the loop below will fix this height
            elif position == 'bottom':
                height = self.size[1] - len(lines)*text_height + last_line_bleed
                height -= text_height  # the loop below will fix this height
            else:
                height = y
                
            for index, line in enumerate(lines):
                if place == 'left':
                    pass
                elif place == 'right':
                    total_size = self.get_text_size(font_filename, font_size, line)
                    x_left = x + box_width - total_size[0]
                elif place == 'center':
                    total_size = self.get_text_size(font_filename, font_size, line)
                    x_left = int(x + ((box_width - total_size[0]) / 2))
                elif place == 'justify':
                    words = line.split()
                    if (index == len(lines) - 1 and not justify_last_line) or \
                    len(words) == 1:
                        continue
                    line_without_spaces = ''.join(words)
                    total_size = self.get_text_size(font_filename, font_size,
                                                    line_without_spaces)
                    space_width = (box_width - total_size[0]) / (len(words) - 1.0)
                    start_x = x
                    for word in words[:-1]:
                        word_size = self.get_text_size(font_filename, font_size,
                                                        word)
                        start_x += word_size[0] + space_width
                    last_word_size = self.get_text_size(font_filename, font_size,
                                                        words[-1])
                    last_word_x = x + box_width - last_word_size[0]
                height += text_height

            if height - y < box_height:
                box_height=None
                break
            else:
                font_size-=1

        # This splits text and creates a multi-lin
        lines = []
        line = []
        words = text.split()
        for word in words:
            new_line = ' '.join(line + [word])
            size = self.get_text_size(font_filename, font_size, new_line)
            text_height = size[1] * line_spacing
            last_line_bleed = text_height - size[1]
            if size[0] <= box_width:
                line.append(word)
            else:
                lines.append(line)
                line = [word]
        if line:
            lines.append(line)
        lines = [' '.join(line) for line in lines if line]
        
        if position == 'middle':
            height = (self.size[1] - len(lines)*text_height + last_line_bleed)/2
            height -= text_height # the loop below will fix this height
        elif position == 'bottom':
            height = self.size[1] - len(lines)*text_height + last_line_bleed
            height -= text_height  # the loop below will fix this height
        else:
            height = y

        for index, line in enumerate(lines):
            if place == 'left':
                self.write_text(img,(x, height), line, font_filename, font_size,
                                color)
            elif place == 'right':
                total_size = self.get_text_size(font_filename, font_size, line)
                x_left = x + box_width - total_size[0]
                self.write_text(img,(x_left, height), line, font_filename,
                                font_size, color)
            elif place == 'center':
                total_size = self.get_text_size(font_filename, font_size, line)
                x_left = int(x + ((box_width - total_size[0]) / 2))
                self.write_text(img,(x_left, height), line, font_filename,
                                font_size, color)
            elif place == 'justify':
                words = line.split()
                if (index == len(lines) - 1 and not justify_last_line) or \
                len(words) == 1:
                    self.write_text(img,(x, height), line, font_filename, font_size,
                                    color)
                    continue
                line_without_spaces = ''.join(words)
                total_size = self.get_text_size(font_filename, font_size,
                                                line_without_spaces)
                space_width = (box_width - total_size[0]) / (len(words) - 1.0)
                start_x = x
                for word in words[:-1]:
                    self.write_text(img,(start_x, height), word, font_filename,
                                    font_size, color)
                    word_size = self.get_text_size(font_filename, font_size,
                                                    word)
                    start_x += word_size[0] + space_width
                last_word_size = self.get_text_size(font_filename, font_size,
                                                    words[-1])
                last_word_x = x + box_width - last_word_size[0]
                self.write_text(img,(last_word_x, height), words[-1], font_filename,
                                font_size, color)
            height += text_height

        return (box_width, height - y)

    def _get_partsbox_data(self, config, part_id):

        PARTSBOX_USER_URL = config["PARTSBOX_USER_URL"]
        PARTSBOX_API_URL = config["PARTSBOX_API_URL"]
        PARTSBOX_API_KEY = config["PARTSBOX_API_KEY"]

        headers = {"Authorization": "APIKey "+PARTSBOX_API_KEY,"Content-Type": "application/json; charset=utf-8"}
        data = {"part/id": part_id}

        response = requests.post(PARTSBOX_API_URL+"/part/get", headers=headers, json=data)
        data=response.json()["data"]

        # Getting stock values per stock location
        stock_status = {}
        for item in data["part/stock"]:
            # if storage location already exist, calcualte the stock level
            if item["stock/storage-id"] in stock_status:
                stock_status[item["stock/storage-id"]]+=item["stock/quantity"]
            # else assing the value
            else:
                stock_status[item["stock/storage-id"]]=item["stock/quantity"]
            #remove locations with 0 stock
            if stock_status[item["stock/storage-id"]] == 0:
                del stock_status[item["stock/storage-id"]]

        # Looking up human readable name
        stock_status_named = {}

        for key, value in stock_status.items():
            response = requests.post(PARTSBOX_API_URL+"/storage/get", headers=headers, json={"storage/id": key})
            data_storage = response.json()

            stock_status_named[data_storage["data"]["storage/name"]]=stock_status[key]

        partsbox_fields = {}
        partsbox_fields["mpn"]=data["part/name"]
        partsbox_fields["desc"]=data["part/linked-choices"]["description"]
        partsbox_fields["location"]=str(stock_status_named).replace("{","").replace("}","").replace("'","")
        partsbox_fields["url"]="https://partsbox.com/irnas/part/"+part_id

        return(partsbox_fields)

    def _generate_partsbox_part(self,img):
        self._text

        with open('partsbox-config.yaml') as f:
            config = yaml.load(f, Loader=yaml.FullLoader)

        partsbox_fields = {}
        # Default values
        partsbox_fields["mpn"]="Placeholder MPN"
        partsbox_fields["desc"]="Placeholder decription of placeholder component on placeholder location"
        partsbox_fields["location"]="Placeholder LOCATION"
        partsbox_fields["url"]="https://PARTSBOX.COM/nonenoenoenoenoenoenoenoene"

        # Check by length if that is partsbox id
        if len(self._text) == 26:
            partsbox_fields=self._get_partsbox_data(config, self._text)
        elif self._text is not ' ':
            lines=self._text.splitlines()
            try:
                partsbox_fields["mpn"]=lines[0]
            except:
                print("Fail")
            
            try:
                partsbox_fields["desc"]=lines[1]
            except:
                print("Fail")

            try:
                partsbox_fields["location"]=lines[2]
            except:
                print("Fail")

            try:
                partsbox_fields["url"]=lines[3]
            except:
                print("Fail")

        color = "black"
        font=self._font_path
        #font = 'Pillow/Tests/fonts/FreeSans.ttf'
        width, height = self._width, self._height

        print("width {} height{} ".format(width,height))

        # top row height as percentage of total
        margin=20
        top_row_height=int(height*0.25)-margin
        mid_row_offset=int(height*0.3)+margin
        mid_row_height=int(height*0.6)-margin
        bottom_row_offset=int(height*0.8)+margin
        bottom_row_height=int(height*0.2)-margin

        # Manufacturere part number
        text_mpn=partsbox_fields["mpn"]
        text_mpn=textwrap.shorten(text_mpn, width=40, placeholder="...")
        self.write_text(img,(margin, margin), text_mpn, font_filename=font, font_size='fill', max_width=width, max_height=top_row_height, color=color)

        self.draw_line(img,(margin,mid_row_offset-margin,int(width*0.7),mid_row_offset-margin))

        # Part description - multi line box, autofit
        text=partsbox_fields["desc"]
        self.write_text_box(img,(margin, mid_row_offset), text, box_width=int(width-height*0.8), box_height=mid_row_height-10, font_filename=font, font_size=30, color=color, place='left')

        self.draw_line(img,(margin,bottom_row_offset-margin,int(width*0.7),bottom_row_offset-margin))

        # Storage location
        text=partsbox_fields["location"]
        text=textwrap.shorten(text, width=50, placeholder="...")
        self.write_text(img,(margin, bottom_row_offset), text, font_filename=font, font_size='fill', max_width=int(width-height*0.8), max_height=bottom_row_height, color=color)

        text=config["PARTSBOX_COMPANY"]
        text=textwrap.shorten(text, width=50, placeholder="...")
        self.write_text(img,(int(width*0.8), int(bottom_row_offset+bottom_row_height/4)), text, font_filename=font, font_size='fill', max_width=int(width-height*0.8), max_height=bottom_row_height/2, color=color)

        # QR code
        qr = QRCode(
            version=1,
            error_correction=constants.ERROR_CORRECT_L,
            box_size=5,
            border=0,
        )
        qr.add_data(partsbox_fields["url"].lower())
        qr.make(fit=True)
        qr_img = qr.make_image(
            fill_color='red' if (255, 0, 0) == self._fore_color else 'black',
            back_color="white")

        w, h = qr_img.size
        img.paste(qr_img,(width-w-20,int(height-h-bottom_row_height)))

        return img
    
    def _generate_partsbox_storage(self,img):
        self._text

        partsbox_fields = {}
        # Default values
        partsbox_fields["location"]="Placeholder LOCATION"
        partsbox_fields["url"]="https://PARTSBOX.COM/nonenoenoenoenoenoenoenoene"

        if self._text is not ' ':
            lines=self._text.splitlines()
            try:
                partsbox_fields["location"]=lines[0]
            except:
                print("Fail")

            try:
                partsbox_fields["url"]=lines[1]
            except:
                print("Fail")

        color = "black"
        font=self._font_path
        #font = 'Pillow/Tests/fonts/FreeSans.ttf'
        width, height = self._width, self._height

        print("width {} height{} ".format(width,height))

        # top row height as percentage of total
        margin=20
        top_row_height=int(height*1)-margin

        # Storage location
        text=partsbox_fields["location"]
        text=textwrap.shorten(text, width=50, placeholder="...")
        self.write_text(img,(margin, 0), text, font_filename=font, font_size='fill', max_width=int(width-height*0.8), max_height=top_row_height, color=color)

        text="irnas.eu"#self.label_company
        text=textwrap.shorten(text, width=50, placeholder="...")
        self.write_text(img,(int(width*0.8), int(0+top_row_height/4)), text, font_filename=font, font_size='fill', max_width=int(width-height*0.8), max_height=top_row_height/2, color=color)

        # QR code
        qr = QRCode(
            version=1,
            error_correction=constants.ERROR_CORRECT_L,
            box_size=5,
            border=0,
        )
        qr.add_data(partsbox_fields["url"].lower())
        qr.make(fit=True)
        qr_img = qr.make_image(
            fill_color='red' if (255, 0, 0) == self._fore_color else 'black',
            back_color="white")

        w, h = qr_img.size
        img.paste(qr_img,(width-w-20,int(height-h)))

        return img

    def generate(self):

        if self._label_content in (LabelContent.PARTSBOX_STORAGE, LabelContent.PARTSBOX_PART):
            if self._label_content is LabelContent.PARTSBOX_PART :
                width, height = (696, int(696*0.4))
                self._width, self._height = width, height 

                imgResult = Image.new('RGB', (width, height), 'white')
                self._generate_partsbox_part(imgResult)
            elif self._label_content is LabelContent.PARTSBOX_STORAGE :
                width, height = (696, int(696*0.3))
                self._width, self._height = width, height 

                imgResult = Image.new('RGB', (width, height), 'white')
                self._generate_partsbox_storage(imgResult)

        else:
            if self._label_content in (LabelContent.QRCODE_ONLY, LabelContent.TEXT_QRCODE):
                img = self._generate_qr()
            elif self._label_content == LabelContent.IMAGE:
                img = self._image
            else:
                img = None

            if img is not None:
                img_width, img_height = img.size
            else:
                img_width, img_height = (0, 0)

            if self._label_content in (LabelContent.TEXT_ONLY, LabelContent.TEXT_QRCODE):
                textsize = self._get_text_size()
            else:
                textsize = (0, 0)

            width, height = self._width, self._height
            margin_left, margin_right, margin_top, margin_bottom = self._label_margin

            if self._label_orientation == LabelOrientation.STANDARD:
                if self._label_type in (LabelType.ENDLESS_LABEL,):
                    height = img_height + textsize[1] + margin_top + margin_bottom
            elif self._label_orientation == LabelOrientation.ROTATED:
                if self._label_type in (LabelType.ENDLESS_LABEL,):
                    width = img_width + textsize[0] + margin_left + margin_right

            if self._label_orientation == LabelOrientation.STANDARD:
                if self._label_type in (LabelType.DIE_CUT_LABEL, LabelType.ROUND_DIE_CUT_LABEL):
                    vertical_offset_text = (height - img_height - textsize[1])//2
                    vertical_offset_text += (margin_top - margin_bottom)//2
                else:
                    vertical_offset_text = margin_top

                vertical_offset_text += img_height
                horizontal_offset_text = max((width - textsize[0])//2, 0)
                horizontal_offset_image = (width - img_width)//2
                vertical_offset_image = margin_top

            elif self._label_orientation == LabelOrientation.ROTATED:
                vertical_offset_text = (height - textsize[1])//2
                vertical_offset_text += (margin_top - margin_bottom)//2
                if self._label_type in (LabelType.DIE_CUT_LABEL, LabelType.ROUND_DIE_CUT_LABEL):
                    horizontal_offset_text = max((width - img_width - textsize[0])//2, 0)
                else:
                    horizontal_offset_text = margin_left
                horizontal_offset_text += img_width
                horizontal_offset_image = margin_left
                vertical_offset_image = (height - img_height)//2

            text_offset = horizontal_offset_text, vertical_offset_text
            image_offset = horizontal_offset_image, vertical_offset_image

            imgResult = Image.new('RGB', (width, height), 'white')
            if img is not None:
                imgResult.paste(img, image_offset)

            if self._label_content in (LabelContent.TEXT_ONLY, LabelContent.TEXT_QRCODE):
                draw = ImageDraw.Draw(imgResult)
                draw.multiline_text(
                    text_offset,
                    self._prepare_text(self._text),
                    self._fore_color,
                    font=self._get_font(),
                    align=self._text_align,
                    spacing=int(self._font_size*((self._line_spacing - 100) / 100)))

        return imgResult

    def _generate_qr(self):
        qr = QRCode(
            version=1,
            error_correction=self._qr_correction,
            box_size=self._qr_size,
            border=0,
        )
        qr.add_data(self._text)
        qr.make(fit=True)
        qr_img = qr.make_image(
            fill_color='red' if (255, 0, 0) == self._fore_color else 'black',
            back_color="white")
        return qr_img

    def _get_text_size(self):
        font = self._get_font()
        img = Image.new('L', (20, 20), 'white')
        draw = ImageDraw.Draw(img)
        return draw.multiline_textsize(
            self._prepare_text(self._text),
            font=font,
            spacing=int(self._font_size*((self._line_spacing - 100) / 100)))

    @staticmethod
    def _prepare_text(text):
        # workaround for a bug in multiline_textsize()
        # when there are empty lines in the text:
        lines = []
        for line in text.split('\n'):
            if line == '':
                line = ' '
            lines.append(line)
        return '\n'.join(lines)

    def _get_font(self):
        return ImageFont.truetype(self._font_path, self._font_size)
