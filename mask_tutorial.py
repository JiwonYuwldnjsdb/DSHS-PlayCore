import sys
import pygame
from pygame.locals import *

pygame.init()
pygame.display.set_caption('mask test')

screen = pygame.display.set_mode((500, 500))

clock = pygame.time.Clock()

img = pygame.image.load('img.png')
img.set_colorkey((0, 0, 0))
img_2 = pygame.image.load('img_2.png')
img_2.set_colorkey((0, 0, 0))
img_loc = (50, 50)

mask = pygame.mask.from_surface(img)
mask_2 = pygame.mask.from_surface(img_2)

show_masks = False

while True:
    screen.fill((0, 0, 0))

    mx, my = pygame.mouse.get_pos()
    if not show_masks:
        screen.blit(img, img_loc)
        screen.blit(img_2, (mx, my))
    else:
        screen.blit(mask.to_surface(unsetcolor=(0, 0, 0, 0), setcolor=(255, 255, 255, 255)), img_loc)
        screen.blit(mask_2.to_surface(unsetcolor=(0, 0, 0, 0), setcolor=(255, 255, 255, 255)), (mx, my))
        outline = [(p[0] + img_loc[0], p[1] + img_loc[1]) for p in mask.outline(every=1)]
        pygame.draw.lines(screen, (255, 0, 255), False, outline, 3)
        overlap_mask = mask.overlap_mask(mask_2, (mx - img_loc[0], my - img_loc[1]))
        screen.blit(overlap_mask.to_surface(unsetcolor=(0, 0, 0, 0), setcolor=(255, 0, 0, 255)), img_loc)
        overlap_centroid = overlap_mask.centroid()
        pygame.draw.circle(screen, (0, 200, 255), (overlap_centroid[0] + img_loc[0], overlap_centroid[1] + img_loc[1]), 10, 3)
        pygame.draw.circle(screen, (0, 200, 255), (overlap_centroid[0] + img_loc[0], overlap_centroid[1] + img_loc[1]), 3, 3)
        print(overlap_mask.count(), mask.overlap_area(mask_2, (mx - img_loc[0], my - img_loc[1])), mask.overlap(mask, (mx - img_loc[0], my - img_loc[1])))

    for event in pygame.event.get():
        if event.type == QUIT:
            pygame.quit()
            sys.exit()
        if event.type == KEYDOWN:
            if event.key == K_m:
                show_masks = not show_masks
            if event.key == K_ESCAPE:
                pygame.quit()
                sys.exit()

    pygame.display.update()
    clock.tick(60)
