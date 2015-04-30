from PIL import Image

def GetImageData(width, height, percentage):
    
    pixels = []
    
    onPixel = (0, 162, 232, 255)
    offPixel = (0, 0, 0, 255)
    
    onWidth = int(width * (float(percentage) / 100))
    
    for y in range(0, height):
        
        for x in range(0, width):
        
            if(x < onWidth):
                pixels.append(onPixel)
            else:
                pixels.append(offPixel)
            
    return pixels

for x in range(1, 101):
    im = Image.new('RGBA', (600, 60))
    im.putdata(GetImageData(600, 60, x))
    im.save("images/progress_" + str(x) + ".png")    