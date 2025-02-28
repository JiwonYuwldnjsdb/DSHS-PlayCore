import pygame
import sys

pygame.init()

# Window setup
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Magic Cat Academy - Drawing Mechanism with Lightning Sign")

clock = pygame.time.Clock()

# Variables for drawing
is_drawing = False
current_stroke = []
font = pygame.font.SysFont(None, 36)
spell_text = ""
spell_text_time = 0

def draw_stroke(surface, stroke, color=(255, 0, 0), width=4):
    if len(stroke) > 1:
        pygame.draw.lines(surface, color, False, stroke, width)

def bounding_box_size(stroke):
    """Return (width, height) of the bounding box of the stroke."""
    xs = [p[0] for p in stroke]
    ys = [p[1] for p in stroke]
    w = max(xs) - min(xs)
    h = max(ys) - min(ys)
    return w, h

# ------------------------------------------------------------
# SIMPLE SHAPE DETECTORS
# ------------------------------------------------------------

def is_horizontal_line(stroke):
    if len(stroke) < 2:
        return False
    xs = [p[0] for p in stroke]
    ys = [p[1] for p in stroke]
    width = max(xs) - min(xs)
    height = max(ys) - min(ys)
    return (width > 100 and height < 0.2 * width)

def is_vertical_line(stroke):
    if len(stroke) < 2:
        return False
    xs = [p[0] for p in stroke]
    ys = [p[1] for p in stroke]
    width = max(xs) - min(xs)
    height = max(ys) - min(ys)
    return (height > 100 and width < 0.2 * height)

# NAIVE “INVERTED V” DETECTION
def is_inverted_v_shape(stroke):
    if len(stroke) < 3:
        return False
    w, h = bounding_box_size(stroke)
    if w < 50 or h < 50:
        return False
    ys = [p[1] for p in stroke]
    apex_index = ys.index(min(ys))  # topmost
    if apex_index == 0 or apex_index == len(stroke) - 1:
        return False
    first_point = stroke[0]
    apex_point = stroke[apex_index]
    last_point = stroke[-1]
    dx1 = apex_point[0] - first_point[0]
    dy1 = apex_point[1] - first_point[1]
    if dx1 == 0:
        return False
    slope1 = dy1 / float(dx1)

    dx2 = last_point[0] - apex_point[0]
    dy2 = last_point[1] - apex_point[1]
    if dx2 == 0:
        return False
    slope2 = dy2 / float(dx2)

    # For a “V”: left->apex slope negative, apex->right slope positive
    if slope1 < -0.3 and slope2 > 0.3:
        return True
    return False

# NAIVE V” DETECTION
def is_v_shape(stroke):
    if len(stroke) < 3:
        return False
    w, h = bounding_box_size(stroke)
    if w < 50 or h < 50:
        return False
    ys = [p[1] for p in stroke]
    apex_index = ys.index(max(ys))  # bottommost
    if apex_index == 0 or apex_index == len(stroke) - 1:
        return False
    first_point = stroke[0]
    apex_point = stroke[apex_index]
    last_point = stroke[-1]
    dx1 = apex_point[0] - first_point[0]
    dy1 = apex_point[1] - first_point[1]
    if dx1 == 0:
        return False
    slope1 = dy1 / float(dx1)

    dx2 = last_point[0] - apex_point[0]
    dy2 = last_point[1] - apex_point[1]
    if dx2 == 0:
        return False
    slope2 = dy2 / float(dx2)

    # For an inverted V: left->apex slope positive, apex->right slope negative
    if slope1 > 0.3 and slope2 < -0.3:
        return True
    return False

# ------------------------------------------------------------
# NAIVE LIGHTNING (/\/) DETECTION
# ------------------------------------------------------------

def is_lightning_sign(stroke):
    """
    Check if the stroke looks like a zigzag with two changes in slope:
      Segment 1 slope: S1
      Segment 2 slope: S2
      Segment 3 slope: S3
    We look for either:
      - negative, positive, negative  (like /\/)
      - positive, negative, positive  (like \/\
    We also ensure the bounding box is large enough.
    """
    if len(stroke) < 4:
        return False
    
    w, h = bounding_box_size(stroke)
    # Ensure it's not a tiny scribble
    if w < 50 and h < 50:
        return False
    
    # Break stroke into 3 segments by index
    n = len(stroke)
    # We'll pick 4 key points:
    p1 = stroke[0]
    p2 = stroke[n // 3]
    p3 = stroke[2 * n // 3]
    p4 = stroke[-1]

    def slope(a, b):
        dx = (b[0] - a[0])
        dy = (b[1] - a[1])
        if dx == 0:
            return 0  # or float('inf'), but let's just say 0
        return dy / float(dx)

    s1 = slope(p1, p2)
    s2 = slope(p2, p3)
    s3 = slope(p3, p4)

    # We'll require a certain magnitude for slope changes
    # (to avoid nearly-flat lines being counted).
    neg_threshold = -0.3
    pos_threshold = 0.3

    patternA = (s1 < neg_threshold and s2 > pos_threshold and s3 < neg_threshold)
    patternB = (s1 > pos_threshold and s2 < neg_threshold and s3 > pos_threshold)

    if patternA or patternB:
        return True
    return False

# ------------------------------------------------------------
# RECOGNITION DISPATCH
# ------------------------------------------------------------
def recognize_spell(stroke):
    if is_horizontal_line(stroke):
        return "Horizontal Line Spell!"
    elif is_vertical_line(stroke):
        return "Vertical Line Spell!"
    elif is_v_shape(stroke):
        return "V Spell!"
    elif is_inverted_v_shape(stroke):
        return "Inverted V Spell!"
    elif is_lightning_sign(stroke):
        return "Lightning Spell!"
    else:
        return ""

# Main loop
running = True
while running:
    dt = clock.tick(60)  # 60 FPS
    screen.fill((30, 30, 30))

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # Left button
                is_drawing = True
                current_stroke = [event.pos]
        
        elif event.type == pygame.MOUSEMOTION:
            if is_drawing:
                current_stroke.append(event.pos)
        
        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1 and is_drawing:
                is_drawing = False
                # Recognize shape
                spell_result = recognize_spell(current_stroke)
                if spell_result:
                    spell_text = spell_result
                    spell_text_time = pygame.time.get_ticks()
                # Clear the stroke (or keep if you want to track them)
                current_stroke = []

    # Draw current stroke
    draw_stroke(screen, current_stroke, (255, 0, 0), 4)

    # Show recognized spell text for 2 seconds
    if spell_text:
        if pygame.time.get_ticks() - spell_text_time < 2000:
            text_surface = font.render(spell_text, True, (255, 255, 255))
            rect = text_surface.get_rect(center=(WIDTH // 2, HEIGHT // 2))
            screen.blit(text_surface, rect)
        else:
            spell_text = ""

    pygame.display.flip()

pygame.quit()
sys.exit()
