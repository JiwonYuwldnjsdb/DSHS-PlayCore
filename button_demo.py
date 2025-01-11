import pygame

pygame.init()

screen = pygame.display.set_mode((800, 600))
pygame.display.set_caption("Button Example")

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)

font = pygame.font.Font(None, 36)

class Button:
    def __init__(self, x, y, image, text, padding=20):
        self.image = image
        self.text = text
        self.font = font
        self.padding = padding

        self.image_rect = self.image.get_rect()
        self.text_surface = self.font.render(self.text, True, BLACK)
        self.text_rect = self.text_surface.get_rect()

        self.width = self.image_rect.width + self.padding + self.text_rect.width
        self.height = max(self.image_rect.height, self.text_rect.height)
        self.rect = pygame.Rect(x, y, self.width, self.height)

        self.hovered = False
        
        self.x_target = 0
        self.x_shift_distance = 40
        self.x_speed = 200
        self.x_offset = 0

    def draw(self, surface):
        surface.blit(self.image, (self.rect.x + self.x_offset, self.rect.y))
        surface.blit(self.text_surface, (self.rect.x + self.x_offset + self.image_rect.width + self.padding, self.rect.y))

    def update(self, mouse_pos):
        self.hovered = self.rect.collidepoint(mouse_pos)
        if self.hovered:
            self.x_target = self.x_shift_distance
        else:
            self.x_target = 0
        
        if abs(self.x_target - self.x_offset) != 0:
            self.x_offset += (self.x_target - self.x_offset) / self.x_speed
            
            if abs(self.x_target - self.x_offset) < 1:
                self.x_offset = self.x_target

# 이미지 불러오기
image = pygame.Surface((50, 50))
image.fill((100, 200, 255))

# 버튼 생성
button = Button(100, 100, image, "Click Me")

# 메인 루프
running = True
while running:
    screen.fill(WHITE)

    # 이벤트 처리
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # 마우스 위치 가져오기
    mouse_pos = pygame.mouse.get_pos()

    # 버튼 업데이트 및 그리기
    button.update(mouse_pos)
    button.draw(screen)

    # 화면 업데이트
    pygame.display.flip()

pygame.quit()
