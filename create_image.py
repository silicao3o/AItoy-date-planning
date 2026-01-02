from PIL import Image, ImageDraw, ImageFont

img = Image.new('RGB', (512, 512), color='#FF6B6B')
draw = ImageDraw.Draw(img)

# 간단한 아이콘 스타일
draw.ellipse([100, 100, 412, 412], fill='white')
draw.ellipse([150, 150, 362, 362], fill='#FF6B6B')
draw.text((200, 230), "서울", fill='white', font=ImageFont.load_default())

img.save('app_icon.png')
print("✅ app_icon.png 생성 완료!")