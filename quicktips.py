import pygame
import random
import sys
import math
from enum import Enum, auto

from localLibraries.PlayCoreLibraries import ScreenObject, blit_fps  # 그대로 사용

pygame.init()

# ---------------------------------------------------------------------------
# Game states
# ---------------------------------------------------------------------------
class GameState(Enum):
    MAIN_MENU = auto()
    TRANSITION = auto()
    ENLARGED = auto()

# ---------------------------------------------------------------------------
# Background floating squares (keep)
# ---------------------------------------------------------------------------
class Square:
    def __init__(self, x, size, speed, angle_speed, screen_height):
        self.size = size
        self.x = x
        self.y = screen_height
        self.speed = speed
        self.angle_speed = angle_speed
        self.angle = 0
        self.alpha = 15.0
        self.surface = pygame.Surface((size, size), pygame.SRCALPHA)
        self.surface.fill((255, 255, 255, int(self.alpha)))

    def update(self, dt):
        self.y -= self.speed * dt
        self.angle = (self.angle + self.angle_speed * dt) % 360
        self.alpha = max(0.0, self.alpha - 1.2 * dt)
        self.surface.fill((255, 255, 255, int(self.alpha)))

    def draw(self, screen):
        rotated_surface = pygame.transform.rotate(self.surface, self.angle)
        rect = rotated_surface.get_rect(center=(self.x, self.y))
        screen.blit(rotated_surface, rect.topleft)

# ---------------------------------------------------------------------------
# Easing / utils
# ---------------------------------------------------------------------------
def clamp01(x): return 0.0 if x < 0.0 else 1.0 if x > 1.0 else x
def ease_out_cubic(t): t = clamp01(t); return 1 - (1 - t) ** 3
def ease_in_out_quad(t): t = clamp01(t); return 2*t*t if t < 0.5 else 1 - (-2*t + 2) ** 2 / 2
def ease_out_back(t, s=1.70158): t = clamp01(t); return 1 + (s + 1)*(t-1)**3 + s*(t-1)**2
def lerp(a, b, t): return a + (b - a) * t

def lerp_rect(r1, r2, t):
    x = lerp(r1.x, r2.x, t)
    y = lerp(r1.y, r2.y, t)
    w = lerp(r1.width, r2.width, t)
    h = lerp(r1.height, r2.height, t)
    return pygame.Rect(int(x), int(y), int(w), int(h))

# ---------------------------------------------------------------------------
# Particles
# ---------------------------------------------------------------------------
class Spark:
    """Open transition burst (outwards)"""
    def __init__(self, pos, color):
        ang = random.uniform(0, 6.28318)
        speed = random.uniform(240, 520)
        v = pygame.math.Vector2(speed, 0).rotate_rad(ang)
        self.vx, self.vy = v.x, v.y
        self.x, self.y = pos
        self.life = random.uniform(0.25, 0.55)
        self.age = 0.0
        self.size = random.randint(2, 4)
        self.color = color

    def update(self, dt):
        self.age += dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vy += 300 * dt  # gravity

    def alive(self): return self.age < self.life

    def draw(self, screen):
        alpha = int(255 * (1 - (self.age / self.life)))
        col = (*self.color, alpha)
        pygame.draw.circle(screen, col, (int(self.x), int(self.y)), self.size)

class ImplodeSpark:
    """Close transition: from edges imploding toward the card"""
    def __init__(self, start_pos, target_pos, color=(255,255,255)):
        self.x, self.y = start_pos
        tx, ty = target_pos
        vec = pygame.math.Vector2(tx - self.x, ty - self.y)
        if vec.length() == 0:
            vec = pygame.math.Vector2(1, 0)
        dirv = vec.normalize()
        speed = random.uniform(260, 540)
        self.vx, self.vy = dirv.x * speed, dirv.y * speed
        self.life = random.uniform(0.28, 0.5)
        self.age = 0.0
        self.size = random.randint(2, 3)
        self.color = color

    def update(self, dt):
        self.age += dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        # gentle decel
        self.vx *= (0.90 ** (dt * 60))
        self.vy *= (0.90 ** (dt * 60))

    def alive(self):
        return self.age < self.life

    def draw(self, screen):
        a = int(255 * (1 - (self.age / self.life)))
        pygame.draw.circle(screen, (*self.color, a), (int(self.x), int(self.y)), self.size)

class RingPulse:
    """Landing ripple ring"""
    def __init__(self, center, max_radius, dur=0.35):
        self.center = (int(center[0]), int(center[1]))
        self.max_r = int(max_radius)
        self.dur = dur
        self.t = 0.0

    def update(self, dt):
        self.t += dt

    def alive(self):
        return self.t < self.dur

    def draw(self, screen):
        p = clamp01(self.t / self.dur)
        r = int(self.max_r * ease_out_cubic(p))
        a = int(180 * (1 - p))
        if r > 0 and a > 0:
            pygame.draw.circle(screen, (255, 255, 255, a), self.center, r, width=3)

# ---------------------------------------------------------------------------
# Card
# ---------------------------------------------------------------------------
class Card:
    def __init__(self, title, color):
        self.title = title
        self.color = color

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
class PlayCoreMenu(ScreenObject):
    DARK_BLUE   = (10, 10, 40)
    DARK_PURPLE = (40, 10, 70)

    def __init__(self, width, height, show_fps=False):
        super().__init__(width, height)
        self.show_fps = show_fps

        font_size = int(self.height * 0.05)
        try:
            self.font = pygame.font.Font("data/fonts/SairaCondensed-Light.ttf", font_size)
        except:
            self.font = pygame.font.SysFont("arial", font_size)

        # State
        self.current_state = GameState.MAIN_MENU

        # Background floaters
        self.squares = []
        self.spawn_rate = 30
        self.frame_count = 0

        # Carousel
        self.setup_cards()

        # Transition
        self.transition_time = 0.0
        self.transition_duration = 0.9
        self.transition_mode = "open"  # or "close"
        self.selected_index = None
        self.transition_start_rect = None
        self.transition_end_rect = None

        # Effects
        self.sparks = []
        self.implode_sparks = []

        # Vignette
        self.vignette = self._build_vignette()

    # ---------------------------- Setup -------------------------------------
    def setup_cards(self):
        titles = ["Instructions", "Game 1", "Game 2", "Game 3", "Game 4", "Game 5", "Game 6"]
        base_colors = [
            (35, 90, 160),
            (190, 120, 60),
            (60, 150, 110),
            (120, 80, 180),
            (180, 70, 120),
            (80, 140, 200),
            (140, 140, 70),
        ]
        self.cards = [Card(t, base_colors[i % len(base_colors)]) for i, t in enumerate(titles)]

        # Tall cards
        self.card_h = int(self.height * 0.70)
        self.card_w = int(self.height * 0.42)
        self.slot_gap = int(self.width * 0.04)
        self.slot = self.card_w + self.slot_gap

        # Scroll
        self.scroll = 0.0
        self.velocity = 0.0
        self.dragging = False
        self.mouse_down = False
        self.click_start_time = 0.0
        self.total_drag_dist = 0.0
        self.target_index = None

        self.min_scroll = 0.0
        self.max_scroll = max(0.0, (len(self.cards) - 1) * self.slot)

        self.card_screen_rects = [pygame.Rect(0, 0, 0, 0) for _ in self.cards]

    # ------------------------- Background / Vignette ------------------------
    def gradient_fill(self, screen, color_top, color_bottom):
        width, height = screen.get_size()
        for y in range(height):
            ratio = y / (height - 1) if height > 1 else 0
            r = int(color_top[0] + (color_bottom[0] - color_top[0]) * ratio)
            g = int(color_top[1] + (color_bottom[1] - color_top[1]) * ratio)
            b = int(color_top[2] + (color_bottom[2] - color_top[2]) * ratio)
            pygame.draw.line(screen, (r, g, b), (0, y), (width, y))

    def spawn_squares(self):
        size = random.randint(self.height // 36, self.height // 12)
        x = random.randint(0, self.width - size)
        speed = random.uniform(20.0, 60.0)
        angle_speed = random.uniform(-45.0, 45.0)
        self.squares.append(Square(x, size, speed, angle_speed, self.height + self.height // 20))

    def update_squares(self, dt):
        for sq in self.squares[:]:
            sq.update(dt)
            if sq.alpha <= 0:
                self.squares.remove(sq)

    def draw_squares(self, screen):
        for sq in self.squares:
            sq.draw(screen)

    def _build_vignette(self):
        # pre-rendered soft vignette
        surf = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        cx, cy = self.width/2, self.height/2
        maxd = (cx**2 + cy**2) ** 0.5
        for y in range(self.height):
            for x in range(self.width):
                d = ((x-cx)**2 + (y-cy)**2) ** 0.5
                t = clamp01((d - maxd*0.55) / (maxd*0.45))
                a = int(160 * t)
                surf.set_at((x, y), (0, 0, 0, a))
        return surf

    # ----------------------------- Card visuals -----------------------------
    def _card_base(self, size, color, alpha=230, radius=24):
        surf = pygame.Surface(size, pygame.SRCALPHA)
        pygame.draw.rect(surf, (*color, alpha), surf.get_rect(), border_radius=radius)
        pygame.draw.rect(surf, (255, 255, 255, int(alpha*0.14)), surf.get_rect(), width=2, border_radius=radius)
        return surf

    def _shine(self, target_surf, t):
        # diagonal sheen sweep (t in [0,1])
        if t <= 0.0 or t >= 1.0: return
        w, h = target_surf.get_size()
        band_w = int(max(12, w * 0.12))
        grad = pygame.Surface((band_w, h*2), pygame.SRCALPHA)
        for x in range(band_w):
            a = int(140 * (1 - abs((x - band_w/2) / (band_w/2))))
            pygame.draw.line(grad, (255, 255, 255, a), (x, 0), (x, h*2))
        grad = pygame.transform.rotate(grad, -25)
        pos_x = int(lerp(-w, w*1.2, t))
        rect = grad.get_rect(center=(pos_x, h//2))
        target_surf.blit(grad, rect)

    def _diagonal_pattern(self, size, phase):
        w, h = size
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        gap = max(12, w//18)
        offset = int((phase % 1.0) * gap)
        for x in range(-h, w + h, gap):
            pygame.draw.line(surf, (255, 255, 255, 16), (x + offset, 0), (x - h + offset, h), 2)
        return surf

    def _pulse_border(self, screen, rect, t, radius=28):
        glow = int(80 + 60 * (0.5 + 0.5 * math.sin(t*2.2)))
        stroke = pygame.Surface((rect.w+20, rect.h+20), pygame.SRCALPHA)
        pygame.draw.rect(stroke, (255, 255, 255, glow), stroke.get_rect(), width=4, border_radius=radius)
        screen.blit(stroke, (rect.x-10, rect.y-10))

    def draw_card(self, screen, rect, color, title, alpha=220, hovered=False):
        # shadow
        shadow = pygame.Surface((rect.w+18, rect.h+18), pygame.SRCALPHA)
        pygame.draw.rect(shadow, (0, 0, 0, 90), shadow.get_rect(), border_radius=28)
        screen.blit(shadow, (rect.x-9, rect.y-6))
        # body
        body = self._card_base((rect.w, rect.h), color, alpha)
        screen.blit(body, rect.topleft)
        # title
        title_surf = self.font.render(title, True, (255, 255, 255))
        title_rect = title_surf.get_rect(center=(rect.centerx, rect.bottom - int(rect.h*0.12)))
        screen.blit(title_surf, title_rect)
        if hovered:
            pygame.draw.rect(screen, (255, 255, 255), rect, width=3, border_radius=24)

    # ----------------------------- Carousel ---------------------------------
    def draw_carousel(self, screen, mouse_pos):
        center_x = self.width // 2
        center_y = int(self.height * 0.56)

        order = []
        for i in range(len(self.cards)):
            cx = (i * self.slot - self.scroll) + center_x
            dist = abs(cx - center_x)
            t = max(0.0, 1.0 - dist / (self.slot))
            scale = 0.9 + 0.2 * t
            order.append((scale, i))
        order.sort()  # small→large so largest draws last

        hovered_index = None
        for _, i in order:
            card = self.cards[i]
            cx = (i * self.slot - self.scroll) + center_x
            dist = abs(cx - center_x)
            t = max(0.0, 1.0 - dist / (self.slot))
            scale = 0.9 + 0.2 * t
            alpha = int(150 + 105 * t)
            w = int(self.card_w * scale)
            h = int(self.card_h * scale)
            rect = pygame.Rect(0, 0, w, h)
            rect.center = (int(cx), center_y)
            self.card_screen_rects[i] = rect

            hovered = rect.collidepoint(mouse_pos)
            if t < 0.65:
                trail = self._card_base((w, h), card.color, alpha=int(alpha*0.35))
                screen.blit(trail, (rect.x + 6, rect.y + 2))
            self.draw_card(screen, rect, card.color, card.title, alpha=alpha, hovered=hovered)
            if hovered: hovered_index = i

        return hovered_index
    
    def _apply_round_mask(self, surf, radius):
        mask = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
        pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(), border_radius=radius)
        # 안쪽은 그대로(흰색=1배), 바깥은 0으로 곱해서 투명 처리
        surf.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)


    # ----------------------------- Transitions ------------------------------
    def _enlarged_target_rect(self):
        # target rect for enlarged card (not full screen)
        final_h = int(self.height * 0.86)
        final_w = int(self.height * 0.52)
        rect = pygame.Rect(0, 0, final_w, final_h)
        rect.center = (self.width // 2, int(self.height * 0.53))
        return rect

    def start_transition(self, index, mode="open"):
        self.current_state = GameState.TRANSITION
        self.transition_mode = mode
        self.selected_index = index
        self.transition_time = 0.0

        if mode == "open":
            self.transition_start_rect = self.card_screen_rects[index].copy()
            self.transition_end_rect = self._enlarged_target_rect()
            # burst outwards
            r = self.transition_start_rect
            cx, cy = r.center
            burst_color = tuple(min(255, c+40) for c in self.cards[index].color)
            for _ in range(48):
                self.sparks.append(Spark((cx + random.uniform(-r.w*0.25, r.w*0.25),
                                          cy + random.uniform(-r.h*0.25, r.h*0.25)), burst_color))
        else:
            # close: reverse with implode + ripple
            self.transition_start_rect = self._enlarged_target_rect()
            self.transition_end_rect = self.card_screen_rects[index].copy()
            self.implode_sparks.clear()
            end_c = self.transition_end_rect.center
            edge_points = []
            M, N = self.width, self.height
            for _ in range(18):
                edge = random.choice(("top","bottom","left","right"))
                if edge == "top":
                    edge_points.append((random.uniform(-40, M+40), -30))
                elif edge == "bottom":
                    edge_points.append((random.uniform(-40, M+40), N+30))
                elif edge == "left":
                    edge_points.append((-30, random.uniform(-40, N+40)))
                else:
                    edge_points.append((M+30, random.uniform(-40, N+40)))
            col = tuple(min(255, c+30) for c in self.cards[index].color)
            for p in edge_points:
                self.implode_sparks.append(ImplodeSpark(p, end_c, color=col))

    def _draw_others_fade(self, screen, t):
        # non-selected cards slide out + fade with trail (during open)
        fade = 1.0 - clamp01(t * 1.2)
        for i, card in enumerate(self.cards):
            if i == self.selected_index: continue
            rect = self.card_screen_rects[i]
            if rect.w <= 0 or rect.h <= 0: continue
            dir_sign = -1 if rect.centerx < self.width//2 else 1
            offset = int(lerp(0, dir_sign * self.width*0.25, ease_out_cubic(1-fade)))
            trail = self._card_base((rect.w, rect.h), card.color, alpha=int(160*fade))
            screen.blit(trail, (rect.x + offset + 10, rect.y + 4))
            body = self._card_base((rect.w, rect.h), card.color, alpha=int(220*fade))
            screen.blit(body, (rect.x + offset, rect.y))

    def update_transition(self, dt, screen):
        self.transition_time += dt
        t = clamp01(self.transition_time / self.transition_duration)

        # Background
        self.gradient_fill(screen, self.DARK_PURPLE, self.DARK_BLUE)
        self.update_squares(dt)
        self.draw_squares(screen)

        if self.transition_mode == "open":
            # Stage: 0~0.22 POP, 0.22~1 MORPH
            t_pop = clamp01(t / 0.22)
            t_morph = clamp01((t - 0.22) / 0.78)
            self._draw_others_fade(screen, t)

            if t < 0.22:
                start = self.transition_start_rect
                scale = 1.0 + 0.08 * ease_out_back(t_pop)
                rot = lerp(-6.0, 4.0, ease_out_cubic(t_pop))
                w = int(start.w * scale)
                h = int(start.h * scale)
                rect = pygame.Rect(0, 0, w, h)
                rect.center = start.center
                body = self._card_base((w, h), self.cards[self.selected_index].color, alpha=240, radius=24)
                self._shine(body, t_pop*0.7)
                body = pygame.transform.rotate(body, rot)
                screen.blit(body, body.get_rect(center=rect.center))
            else:
                start = self.transition_start_rect
                end = self.transition_end_rect
                et = ease_in_out_quad(t_morph)
                now_rect = lerp_rect(start, end, et)
                radius = max(12, int(24 * (1 - et*0.85)))
                body = self._card_base((now_rect.w, now_rect.h), self.cards[self.selected_index].color, alpha=240, radius=radius)
                self._shine(body, clamp01((t_morph - 0.15) / 0.6))
                phase = (pygame.time.get_ticks()/1000.0) * 0.25
                body.blit(self._diagonal_pattern((now_rect.w, now_rect.h), phase), (0, 0))
                screen.blit(body, now_rect.topleft)

        else:
            # ---------------- CLOSE: lift + reverse sheen + ghost trails + implode + ripple
            # show carousel faintly (return feeling)
            self.draw_carousel(screen, (-1, -1))

            start = self.transition_start_rect
            end = self.transition_end_rect

            # timing: 0~0.18 lift/tilt, 0.18~1 morph/land
            t_lift = clamp01(t / 0.18)
            t_morph = clamp01((t - 0.18) / 0.82)
            et = ease_in_out_quad(t_morph)

            now_rect = lerp_rect(start, end, et)
            lift = int(lerp(-self.height * 0.035, 0, et))  # small lift at start
            now_rect.centery += lift

            radius = max(12, int(24 * (1 - (et * 0.85))))
            body = self._card_base((now_rect.w, now_rect.h), self.cards[self.selected_index].color, alpha=240, radius=radius)
            # reverse sheen (right->left feel)
            self._shine(body, 1.0 - clamp01((t_morph - 0.05) / 0.55))
            phase = (pygame.time.get_ticks()/1000.0) * 0.16
            self._apply_round_mask(body, radius)
            body.blit(self._diagonal_pattern((now_rect.w, now_rect.h), phase), (0, 0))

            # ghost trails (3 layers)
            for g in range(1, 4):
                gt = clamp01(et - g * 0.06)
                if gt <= 0: continue
                gr = lerp_rect(start, end, gt)
                ghost = self._card_base((gr.w, gr.h), self.cards[self.selected_index].color,
                                        alpha=int(80 * (1 - g/4)), radius=max(12, int(24 * (1 - (gt * 0.85)))))
                screen.blit(ghost, (gr.x + (4-g)*4, gr.y + (4-g)*2))

            # main body
            screen.blit(body, now_rect.topleft)

            # implode particles
            for sp in self.implode_sparks[:]:
                sp.update(dt)
                if sp.alive():
                    sp.draw(screen)
                else:
                    self.implode_sparks.remove(sp)
            
            # vignette fades out while closing
            vig_alpha = int(160 * (1.0 - t))
            if vig_alpha > 0:
                v = self.vignette.copy()
                v.set_alpha(vig_alpha)
                screen.blit(v, (0, 0))

        # Sparks for open burst
        for sp in self.sparks[:]:
            sp.update(dt)
            if not sp.alive(): self.sparks.remove(sp)
            else: sp.draw(screen)

        if t >= 1.0:
            self.current_state = GameState.ENLARGED if self.transition_mode == "open" else GameState.MAIN_MENU
            if self.current_state == GameState.MAIN_MENU:
                # reset effects
                self.sparks.clear()
                self.implode_sparks.clear()

    # --------------------------- Enlarged mode -------------------------------
    def draw_enlarged(self, screen):
        # dim background
        dim = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 120))
        screen.blit(dim, (0, 0))

        rect = self._enlarged_target_rect()
        card = self.cards[self.selected_index]
        t = pygame.time.get_ticks() / 1000.0
        breathe = 1.0 + 0.012 * math.sin(t * 2.2)
        bw, bh = int(rect.w * breathe), int(rect.h * breathe)
        brect = pygame.Rect(0, 0, bw, bh); brect.center = rect.center

        # pulse border glow
        self._pulse_border(screen, brect, t)

        # body + pattern + gradient + sheen
        body = self._card_base((bw, bh), card.color, alpha=240, radius=28)
        diag = self._diagonal_pattern((bw, bh), (t * 0.18) % 1.0)
        body.blit(diag, (0, 0))
        grad = pygame.Surface((bw, bh), pygame.SRCALPHA)
        for y in range(bh):
            a = int(70 * (1 - y / max(1, bh)))
            pygame.draw.line(grad, (255, 255, 255, a), (0, y), (bw, y))
        body.blit(grad, (0, 0))
        self._shine(body, (math.sin(t*1.0) * 0.5 + 0.5))
        self._apply_round_mask(body, radius=28)
        screen.blit(body, brect.topleft)

        # title
        title_surf = self.font.render(card.title, True, (255, 255, 255))
        title_rect = title_surf.get_rect(center=(brect.centerx, brect.top + int(bh*0.12)))
        screen.blit(title_surf, title_rect)

        # chips (example)
        def chip(text, cx, cy):
            pad_x, pad_y = 16, 8
            chip_text = self.font.render(text, True, (20, 20, 30))
            w, h = chip_text.get_width()+pad_x*2, chip_text.get_height()+pad_y*2
            chip_surf = pygame.Surface((w, h), pygame.SRCALPHA)
            pygame.draw.rect(chip_surf, (255, 255, 255, 210), chip_surf.get_rect(), border_radius=18)
            pygame.draw.rect(chip_surf, (0, 0, 0, 35), chip_surf.get_rect(), width=2, border_radius=18)
            chip_surf.blit(chip_text, (pad_x, pad_y))
            rect = chip_surf.get_rect(center=(cx, cy))
            screen.blit(chip_surf, rect)

        cy = title_rect.bottom + 30
        chip_spacing = 14
        chips = ["Single Play", "Casual", "New"]
        total_w = 0
        widths = []
        for c in chips:
            tw = self.font.size(c)[0] + 32
            widths.append(tw)
            total_w += tw
        total_w += chip_spacing*(len(chips)-1)
        start_x = brect.centerx - total_w//2
        x = start_x
        for i, c in enumerate(chips):
            cw = widths[i]
            chip(c, x + cw//2, cy)
            x += cw + chip_spacing

        # footer hint
        hint = "Click outside or press Esc to close"
        hint_surf = self.font.render(hint, True, (230, 230, 235))
        hint_rect = hint_surf.get_rect(center=(brect.centerx, brect.bottom - int(bh*0.08)))
        screen.blit(hint_surf, hint_rect)

    # ------------------------------- Input ----------------------------------
    def handle_input(self, event, dt):
        if self.current_state == GameState.MAIN_MENU:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self.mouse_down = True
                self.dragging = True
                self.click_start_time = pygame.time.get_ticks() / 1000.0
                self.total_drag_dist = 0.0

            elif event.type == pygame.MOUSEMOTION and self.dragging and self.mouse_down:
                dx, _ = event.rel
                self.scroll -= dx
                self.total_drag_dist += abs(dx)

            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                self.mouse_down = False
                was_drag = self.total_drag_dist > 6
                click_time = pygame.time.get_ticks() / 1000.0 - self.click_start_time
                self.dragging = False

                if not was_drag and click_time < 0.25:
                    mx, my = pygame.mouse.get_pos()
                    clicked = None
                    for i, r in enumerate(self.card_screen_rects):
                        if r.collidepoint(mx, my):
                            clicked = i
                            break
                    if clicked is None:
                        clicked = round(self.scroll / self.slot)

                    if clicked != round(self.scroll / self.slot):
                        self.target_index = clicked
                    else:
                        self.start_transition(clicked, mode="open")

            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_RIGHT, pygame.K_d):
                    self.target_index = min(len(self.cards) - 1, round(self.scroll / self.slot) + 1)
                elif event.key in (pygame.K_LEFT, pygame.K_a):
                    self.target_index = max(0, round(self.scroll / self.slot) - 1)

        elif self.current_state == GameState.ENLARGED:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.start_transition(self.selected_index, mode="close")
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if not self._enlarged_target_rect().collidepoint(pygame.mouse.get_pos()):
                    self.start_transition(self.selected_index, mode="close")

    # -------------------------------- Loop ----------------------------------
    def loop(self, screen):
        clock = pygame.time.Clock()
        running = True

        while running:
            dt_ms = clock.tick(60)
            dt = dt_ms / 1000.0

            self.frame_count += 1
            if self.frame_count % self.spawn_rate == 0:
                self.spawn_squares()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                self.handle_input(event, dt)

            # inertial scroll + snap (main only)
            if self.current_state == GameState.MAIN_MENU:
                prev_scroll = self.scroll
                if not self.dragging:
                    self.scroll += self.velocity * dt
                    self.velocity *= (0.92 ** (dt * 60))
                else:
                    if dt > 0:
                        self.velocity = (self.scroll - prev_scroll) / dt

                if not self.dragging:
                    if self.target_index is not None:
                        target = self.target_index * self.slot
                        self.scroll = lerp(self.scroll, target, min(10.0 * dt, 1.0))
                        if abs(self.scroll - target) < 0.5:
                            self.scroll = target
                            self.target_index = None
                    else:
                        if abs(self.velocity) < 10.0:
                            nearest = round(self.scroll / self.slot)
                            target = nearest * self.slot
                            self.scroll = lerp(self.scroll, target, min(8.0 * dt, 1.0))

                if self.scroll < self.min_scroll:
                    self.scroll = lerp(self.scroll, self.min_scroll, min(12.0 * dt, 1.0))
                    if not self.dragging: self.velocity = 0.0
                if self.scroll > self.max_scroll:
                    self.scroll = lerp(self.scroll, self.max_scroll, min(12.0 * dt, 1.0))
                    if not self.dragging: self.velocity = 0.0

            # background
            self.gradient_fill(screen, self.DARK_PURPLE, self.DARK_BLUE)
            self.update_squares(dt)
            self.draw_squares(screen)

            # render by state
            if self.current_state == GameState.MAIN_MENU:
                self.draw_carousel(screen, pygame.mouse.get_pos())

            elif self.current_state == GameState.TRANSITION:
                self.update_transition(dt, screen)

            elif self.current_state == GameState.ENLARGED:
                # keep carousel dimly visible under dim layer
                self.draw_carousel(screen, (-1, -1))
                self.draw_enlarged(screen)

            if self.show_fps:
                blit_fps(screen, clock)
            pygame.display.flip()

# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    WIDTH, HEIGHT = 1280, 720
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("PlayCoreMenu — Card Enlarged Mode")

    menu_screen = PlayCoreMenu(WIDTH, HEIGHT, show_fps=True)
    menu_screen.loop(screen)
