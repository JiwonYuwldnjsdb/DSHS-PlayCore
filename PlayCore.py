import pygame
import random
import sys
import math
import os
from typing import Dict, List, Tuple
from collections import deque

from localLibraries.PlayCoreLibraries import ScreenObject, blit_fps

pygame.init()

# ----------------------------- Tunables ------------------------------------
# Nebula background version
# 배경 이미지는 아래 경로에 둔다. 이 파일과 같은 프로젝트 루트 기준.
MENU_BACKGROUND_IMAGE = "data/menu/background.png"

def asset_path(path: str | None) -> str | None:
    """상대 경로를 이 py 파일 기준으로 안정적으로 변환."""
    if not path:
        return None
    if os.path.isabs(path):
        return path
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), path)

# Clean redesign notes
# - Layout is unchanged. Only the visual skin was redesigned.
# - Menu image sizes at WIDTH=1280, HEIGHT=720:
#   * How To / large tile: 240 x 240 px
#   * Game tile: 302 x 144 px
# - General formula:
#   * large tile = H/3 x H/3
#   * game tile  = (2H/5 + H/50) x H/5
# - Images are center-cropped automatically. If the file is missing, the tile
#   uses its fallback solid color, so you can add images later.
SHINE_ENABLED   = False
PATTERN_ALPHA   = 0       # 줄무늬 제거: 이미지/단색 카드만 보이게 함
PATTERN_GAP_K   = 0.32
PATTERN_SPEED   = 0.0
PATTERN_ANGLE   = -18
PATTERN_FRAMES  = 1

# 업로드한 우주/성운 배경에 맞춘 저채도 다크 네이비 팔레트.
# 너무 쨍한 네온을 피하고, 배경의 파란빛만 은은하게 이어받는다.
MODERN_BG_TOP       = (3, 7, 18)
MODERN_BG_BOTTOM    = (1, 4, 12)
MODERN_PANEL        = (18, 25, 38)
MODERN_TEXT         = (238, 243, 250)
MODERN_MUTED_TEXT   = (132, 148, 172)
MODERN_ACCENT       = (126, 152, 190)
MODERN_ACCENT_2     = (54, 73, 104)

# ----------------------------- Background Squares --------------------------
class Square:
    def __init__(self, x, size, speed, angle_speed, screen_height):
        self.size = size
        self.x = x
        self.y = screen_height
        self.speed = speed
        self.angle_speed = angle_speed
        self.angle = 0
        self.alpha = 0.0
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        surf.fill((180, 180, 170, int(self.alpha)))
        # convert_alpha로 포맷 고정 (속도향상)
        self.surface = surf.convert_alpha()

    def update(self, dt):
        self.y -= self.speed * dt
        self.angle = (self.angle + self.angle_speed * dt) % 360
        self.alpha = max(0.0, self.alpha - 1.2 * dt)
        # alpha만 업데이트 → 새 Surface 생성 없이 fill
        self.surface.fill((180, 180, 170, int(self.alpha)))

    def draw(self, screen):
        # 회전은 비용이 큼 → 개수는 작고, 나머지 최적화로 여유 확보
        rotated_surface = pygame.transform.rotate(self.surface, self.angle)
        rect = rotated_surface.get_rect(center=(self.x, self.y))
        screen.blit(rotated_surface, rect.topleft)

# --------------------------------- Helpers ---------------------------------
def clamp01(x): return 0.0 if x < 0 else 1.0 if x > 1 else x
def lerp(a, b, t): return a + (b - a) * t

# ----------------------------- Internal Caches ------------------------------
class RoundMaskCache:
    def __init__(self):
        self.cache: Dict[Tuple[int,int,int], pygame.Surface] = {}
    def get(self, w, h, radius):
        key = (w, h, radius)
        surf = self.cache.get(key)
        if surf is None:
            mask = pygame.Surface((w, h), pygame.SRCALPHA)
            pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(), border_radius=radius)
            self.cache[key] = mask
            surf = mask
        return surf

class ShadowCache:
    def __init__(self):
        self.cache: Dict[Tuple[int,int,int], pygame.Surface] = {}
    def get(self, w, h, radius):
        key = (w, h, radius)
        sh = self.cache.get(key)
        if sh is None:
            # Soft layered shadow: modern card 느낌. Blur 없이도 충분히 부드럽게 보이도록
            # 여러 알파 레이어를 겹친다.
            pad = 30
            sh = pygame.Surface((w + pad * 2, h + pad * 2), pygame.SRCALPHA)
            for k, alpha in enumerate((20, 13, 8, 4)):
                inset = k * 6
                rect = pygame.Rect(inset, inset, w + pad * 2 - inset * 2, h + pad * 2 - inset * 2)
                pygame.draw.rect(sh, (0, 2, 10, alpha), rect, border_radius=radius + 18)
            self.cache[key] = sh.convert_alpha()
        return sh

class CardBodyCache:
    def __init__(self):
        self.cache: Dict[Tuple[int,int,int,Tuple[int,int,int],int], pygame.Surface] = {}
    def get(self, w, h, radius, color, alpha=245):
        key = (w, h, radius, color, alpha)
        body = self.cache.get(key)
        if body is None:
            body = pygame.Surface((w, h), pygame.SRCALPHA)
            pygame.draw.rect(body, (*color, alpha), (0, 0, w, h), border_radius=radius)
            # glass highlight border
            pygame.draw.rect(body, (210, 225, 245, 20), (0, 0, w, h), width=1, border_radius=radius)
            pygame.draw.rect(body, (0, 0, 0, 30), (1, 1, w - 2, h - 2), width=1, border_radius=max(0, radius - 1))
            self.cache[key] = body.convert_alpha()
        return body

class GradOverlayCache:
    def __init__(self):
        self.cache: Dict[Tuple[int,int,int], pygame.Surface] = {}
    def get(self, w, h, radius):
        key = (w, h, radius)
        g = self.cache.get(key)
        if g is None:
            grad = pygame.Surface((w, h), pygame.SRCALPHA)
            for y in range(h):
                a = int(6 * (1 - y / max(1, h)))
                pygame.draw.line(grad, (255, 255, 255, a), (0, y), (w, y))
            # 라운드 마스크 적용으로 모서리 누락 이슈 해결
            mask = RoundMaskCache().get(w, h, radius)
            grad.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            g = grad.convert_alpha()
            self.cache[key] = g
        return g

class PatternFramesCache:
    """타일 크기별로 대각선 줄무늬를 프리컴퓨트하여 회전 비용 제거."""
    def __init__(self):
        self.cache: Dict[Tuple[int,int,int,float,int], List[pygame.Surface]] = {}
    def build_frames(self, w, h, radius, gap, angle_deg, alpha, nframes):
        key = (w, h, radius, angle_deg, nframes)
        if key in self.cache:
            return self.cache[key]
        frames: List[pygame.Surface] = []
        for i in range(nframes):
            phase = i / nframes
            # 원본 코드와 동일한 알고리즘으로 생성하되, 사전 계산만 수행
            diag_hyp = int(math.hypot(w, h))
            pad = diag_hyp // 2 + 2
            canvas = pygame.Surface((w + pad*2, h + pad*2), pygame.SRCALPHA)
            offset = int((phase % 1.0) * gap)
            col = (235, 238, 245, alpha)
            for x in range(-diag_hyp, w + diag_hyp, gap):
                pygame.draw.line(canvas, col, (x + offset, 0), (x - diag_hyp + offset, h + diag_hyp), 1)
            canvas = pygame.transform.rotate(canvas, angle_deg)
            # 잘라내기
            rect = canvas.get_rect(center=(w//2 + pad, h//2 + pad))
            strip = pygame.Surface((w, h), pygame.SRCALPHA)
            strip.blit(canvas, (-rect.x, -rect.y))
            # 라운드 마스크 적용
            mask = RoundMaskCache().get(w, h, radius)
            strip.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            frames.append(strip.convert_alpha())
        self.cache[key] = frames
        return frames


class TileVisualCache:
    """Builds image-backed menu cards. Missing image => solid fallback color."""
    def __init__(self, mask_cache: RoundMaskCache):
        self.cache: Dict[Tuple[str, int, int, int, Tuple[int, int, int]], pygame.Surface] = {}
        self.mask_cache = mask_cache

    def _cover_scale(self, surf: pygame.Surface, w: int, h: int) -> pygame.Surface:
        sw, sh = surf.get_size()
        if sw <= 0 or sh <= 0:
            fallback = pygame.Surface((w, h), pygame.SRCALPHA)
            fallback.fill((38, 38, 38, 255))
            return fallback

        scale = max(w / sw, h / sh)
        nw, nh = max(1, int(sw * scale)), max(1, int(sh * scale))
        scaled = pygame.transform.smoothscale(surf, (nw, nh))
        cropped = pygame.Surface((w, h), pygame.SRCALPHA)
        cropped.blit(scaled, ((w - nw) // 2, (h - nh) // 2))
        return cropped

    def get(self, image_path: str | None, w: int, h: int, radius: int, fallback_color: Tuple[int, int, int]) -> pygame.Surface:
        key = (image_path or "__solid__", w, h, radius, fallback_color)
        cached = self.cache.get(key)
        if cached is not None:
            return cached

        surface = pygame.Surface((w, h), pygame.SRCALPHA)
        loaded = None
        if image_path:
            try:
                loaded = pygame.image.load(asset_path(image_path)).convert_alpha()
            except Exception:
                loaded = None

        if loaded is not None:
            surface.blit(self._cover_scale(loaded, w, h), (0, 0))
        else:
            # Image가 없으면 임시 단색 배경.
            surface.fill((*fallback_color, 255))

        # 이미지 위 하단 가독성용 반투명 회색 그라데이션.
        # 위쪽은 거의 그대로 두고, 아래쪽으로 갈수록 더 진해지게 함.
        bottom_gradient = pygame.Surface((w, h), pygame.SRCALPHA)
        for y in range(h):
            t = y / max(1, h - 1)
            # 카드 높이의 약 35% 지점부터 서서히 어두워지고,
            # 하단 텍스트 영역은 더 진한 회색 필름이 깔림.
            p = max(0.0, (t - 0.2) / 0.8)
            a = min(255,int(100 + 150 * (p ** 1.7)))
            pygame.draw.line(bottom_gradient, (28, 29, 34, a), (0, y), (w, y), 10)
        surface.blit(bottom_gradient, (0, 0))

        # rounded mask + clean modern outline
        mask = self.mask_cache.get(w, h, radius)
        surface.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        pygame.draw.rect(surface, (215, 230, 255, 24), (0, 0, w, h), width=1, border_radius=radius)
        self.cache[key] = surface.convert_alpha()
        return self.cache[key]


# ------------------------------ Modal Dialog --------------------------------
class ModalDialog:
    """블러킹 모달: 배경 딤 + 라운드 카드 + 버튼 2개 (캐시 적용)"""
    def __init__(self, menu, title, message, yes_text="Yes", cancel_text="Cancel"):
        self.menu = menu
        self.title = title
        self.message = message
        self.yes_text = yes_text
        self.cancel_text = cancel_text
        self.result = None  # True=confirm, False=cancel, None=pending

        W, H = menu.width, menu.height
        dw = int(W * 0.56)
        dh = int(H * 0.34)
        self.rect = pygame.Rect(0, 0, dw, dh)
        self.rect.center = (W//2, H//2)

        # 버튼 배치
        bw = int(dw * 0.28)
        bh = int(dh * 0.22)
        gap = int(dw * 0.06)
        y = self.rect.bottom - bh - int(dh * 0.10)
        cx = self.rect.centerx
        self.btn_yes = pygame.Rect(cx - gap//2 - bw, y, bw, bh)
        self.btn_cancel = pygame.Rect(cx + gap//2, y, bw, bh)

        # 폰트
        self.title_font = menu.fontH1
        self.text_font  = menu.fontP

        self.hover_yes = False
        self.hover_cancel = False

        # --- 캐시된 정적 요소들 ---
        self._dim = pygame.Surface((menu.width, menu.height), pygame.SRCALPHA)
        self._dim.fill((0, 0, 0, 140))

        # 그림자/본체
        self._shadow = pygame.Surface((self.rect.w + 52, self.rect.h + 52), pygame.SRCALPHA)
        for k, alpha in enumerate((38, 24, 14, 8)):
            inset = k * 8
            rect = pygame.Rect(inset, inset, self.rect.w + 52 - inset * 2, self.rect.h + 52 - inset * 2)
            pygame.draw.rect(self._shadow, (0, 0, 0, alpha), rect, border_radius=34)

        self._body = pygame.Surface((self.rect.w, self.rect.h), pygame.SRCALPHA)
        menu.gradient_fill(self._body, (21, 31, 48), (9, 15, 27))
        self.menu._apply_round_mask(self._body, radius=26)
        pygame.draw.rect(self._body, (210, 225, 245, 26), self._body.get_rect(), width=1, border_radius=26)

        # 텍스트 사전 렌더
        self._title_s = self.title_font.render(self.title, True, MODERN_TEXT)
        self._msg_s = self.text_font.render(self.message, True, MODERN_MUTED_TEXT)

        # 버튼 비트맵 (hover on/off)
        self._btn_yes_normal = self._render_button(self.btn_yes.size, self.yes_text, False)
        self._btn_yes_hover  = self._render_button(self.btn_yes.size, self.yes_text, True)
        self._btn_cancel_normal = self._render_button(self.btn_cancel.size, self.cancel_text, False)
        self._btn_cancel_hover  = self._render_button(self.btn_cancel.size, self.cancel_text, True)

    def _render_button(self, size, text, hovered):
        w, h = size
        base = (204, 216, 235, 225) if hovered else (158, 177, 205, 190)
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(surf, base, (0, 0, w, h), border_radius=18)
        pygame.draw.rect(surf, (255, 255, 255, 42), (0, 0, w, h), width=1, border_radius=18)
        ts = self.text_font.render(text, True, (8, 13, 24))
        tr = ts.get_rect(center=(w//2, h//2))
        surf.blit(ts, tr)
        return surf.convert_alpha()

    def draw(self, screen):
        # 배경 딤
        screen.blit(self._dim, (0, 0))
        # 그림자 + 본체
        screen.blit(self._shadow, (self.rect.x - 26, self.rect.y - 24))
        screen.blit(self._body, self.rect.topleft)

        # 텍스트
        title_r = self._title_s.get_rect(center=(self.rect.centerx, self.rect.top + int(self.rect.h * 0.18)))
        msg_r = self._msg_s.get_rect(center=(self.rect.centerx, title_r.bottom + int(self.rect.h * 0.16)))
        screen.blit(self._title_s, title_r)
        screen.blit(self._msg_s, msg_r)

        # 버튼
        screen.blit(self._btn_yes_hover if self.hover_yes else self._btn_yes_normal, self.btn_yes.topleft)
        screen.blit(self._btn_cancel_hover if self.hover_cancel else self._btn_cancel_normal, self.btn_cancel.topleft)

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            pos = event.pos
            self.hover_yes = self.btn_yes.collidepoint(pos)
            self.hover_cancel = self.btn_cancel.collidepoint(pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pass
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            pos = event.pos
            if self.btn_yes.collidepoint(pos):
                self.result = True
            elif self.btn_cancel.collidepoint(pos):
                self.result = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                self.result = True
            elif event.key == pygame.K_ESCAPE:
                self.result = False

# --------------------------------- Menu ------------------------------------
class PlayCoreMenu(ScreenObject):
    DARK_BLUE   = MODERN_BG_BOTTOM
    DARK_PURPLE = MODERN_BG_TOP

    def __init__(self, width, height, show_fps=False):
        super().__init__(width, height)
        self.show_fps = show_fps

        # Fonts
        self.fontH1 = pygame.font.Font("data/fonts/SairaCondensed-Light.ttf", 50)
        self.fontP  = pygame.font.Font("data/fonts/SairaCondensed-Light.ttf", 25)
        self.fontSmall = pygame.font.Font("data/fonts/SairaCondensed-Light.ttf", 18)

        # Title text (사전 렌더)
        self.title_text_surface = self.fontH1.render("DSHS PlayCore", True, MODERN_TEXT)
        self.small_title_text_surface = self.fontP.render("Made by STATIC Jiwon Yu & Yuseung Jang", True, MODERN_MUTED_TEXT)

        # Tiles: 배치는 그대로, visual skin만 새로 적용.
        # image가 없거나 경로가 틀리면 fallback_color 단색 배경으로 자동 대체된다.
        base = [
            {
                "title": "How To",
                "image": "data/menu/background.png",
                "fallback_color": (23, 34, 52),
                "eyebrow": "Guide"
            },
            {
                "title": "Lynez",
                "image": "data/menu/lynez.png",
                "fallback_color": (28, 38, 55),
                "eyebrow": "Puzzle"
            },
            {
                "title": "Magic Cat Academy",
                "image": "data/menu/magic_cat_academy.png",
                "fallback_color": (34, 33, 50),
                "eyebrow": "Arcade"
            },
            {
                "title": "Airship",
                "image": "data/menu/airship.png",
                "fallback_color": (24, 42, 52),
                "eyebrow": "Action"
            }
        ]
        # dummies = [{
        #     "title": f"Game {i}",
        #     "image": f"data/images/menu/game_{i}.png",
        #     "fallback_color": (40 + (i*15)%120, 80, 130),
        #     "eyebrow": "Game"
        # } for i in range(6, 22)]
        self.tiles = base #+ dummies

        # 타일별 줄무늬 애니 위상/속도 랜덤
        self.tile_anim_meta = [{"phase0": random.random(), "speed": random.uniform(0.7, 1.3)} for _ in self.tiles]

        # Layout & scrolling
        self.tile_rects = []   # content-space rects
        self.anchors = []      # 스냅 지점
        self._build_layout_flow_offset()

        self.scroll_x = 0.0
        self.snap_target_x = None
        self.dragging = False
        self.mouse_down = False
        self.drag_start_x = 0
        self.scroll_start_x = 0.0
        self.total_drag = 0.0
        self.hovered_tile_index = None

        # Inertia scroll state
        self.inertia_v = 0.0  # pixels/sec in scroll space
        self._vel_samples = deque(maxlen=8)
        self._last_drag_dir = 0  # -1 (left), 0 (none), 1 (right)

        # Background squares
        self.squares: List[Square] = []
        self.spawn_rate = 999999  # clean 버전에서는 배경 사각형 애니메이션 비활성화
        self.frame_count = 0

        # Modal
        self.modal: ModalDialog | None = None
        self.pending_select_title = None

        # ---- 새로 추가된 캐시들 ----
        self._mask_cache = RoundMaskCache()
        self._shadow_cache = ShadowCache()
        self._card_body_cache = CardBodyCache()
        self._grad_overlay_cache = GradOverlayCache()
        self._pattern_frames_cache = PatternFramesCache()
        self._tile_visual_cache = TileVisualCache(self._mask_cache)

        # 배경 그라디언트(고정) 사전 생성
        self._bg = self._render_modern_background()

        # 타일 정적 자산 프리컴퓨트 (기본 크기+hover 크기)
        self._tile_assets: Dict[int, Dict[str, object]] = {}
        self._precompute_tile_assets()

        # 타일 텍스트 사전 렌더
        self._tile_title_surf = [self.fontP.render(t["title"], True, MODERN_TEXT) for t in self.tiles]
        self._tile_eyebrow_surf = [self.fontSmall.render(t.get("eyebrow", "Game").upper(), True, (150, 170, 198)) for t in self.tiles]

    # ----------------------------- Layout -----------------------------------
    def _build_layout_flow_offset(self):
        self.tile_rects.clear()
        self.anchors.clear()

        H = self.height
        x_margin = H / 10
        y_margin = H / 3
        spacing  = H / 50

        # Quick tips (큰 타일)
        quick_w = H / 3
        quick_h = H / 3
        quick_rect = pygame.Rect(x_margin, y_margin, quick_w, quick_h)
        self.tile_rects.append(quick_rect)

        # 동일 크기 타일
        game_w  = H / 5 * 2 + spacing
        game_h  = H / 5

        # 상단/하단 Y 좌표
        top_y    = y_margin + quick_h - game_h
        bottom_y = y_margin + quick_h + spacing

        # 상단 첫 컬럼 x(Quick 오른쪽)
        top_first_x = x_margin + quick_w + spacing
        # 하단 첫 컬럼 x: 왼쪽 여백(x_margin)에서 바로 시작 → 빈 공간 제거
        bottom_first_x = x_margin

        # 각각 오른쪽으로 이어붙임 (홀수=상단, 짝수=하단)
        top_x, bottom_x = top_first_x, bottom_first_x
        last_right = quick_rect.right

        for i in range(1, len(self.tiles)):
            if i % 2 == 0:
                rect = pygame.Rect(top_x, top_y, game_w, game_h)
                top_x += game_w + spacing
            else:
                rect = pygame.Rect(bottom_x, bottom_y, game_w, game_h)
                bottom_x += game_w + spacing
            self.tile_rects.append(rect)
            last_right = max(last_right, rect.right)

        # 스냅 앵커
        self.anchors.append(0.0)  # Quick tips 영역
        lefts = set()
        n_top = math.ceil((len(self.tiles) - 1) / 2.0)
        for k in range(n_top):
            lefts.add(top_first_x + k * (game_w + spacing))
        n_bottom = (len(self.tiles) - 1) // 2
        for k in range(n_bottom):
            lefts.add(bottom_first_x + k * (game_w + spacing))
        for L in sorted(lefts):
            self.anchors.append(max(0.0, L - x_margin))

        # 스크롤 한계
        content_width = last_right + x_margin
        self.content_width = content_width
        self.max_scroll_x = max(0.0, content_width - self.width)
        self.anchors = [max(0.0, min(a, self.max_scroll_x)) for a in self.anchors]

        # 타이틀 위치
        self.title_text_pos = (x_margin, x_margin)
        self.small_title_pos = (x_margin, x_margin + 48 + spacing)

    # --------------------------- Visual helpers -----------------------------
    def _apply_round_mask(self, surf, radius):
        mask = self._mask_cache.get(surf.get_width(), surf.get_height(), radius)
        surf.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

    def _tile_shadow(self, rect, radius=24):
        return self._shadow_cache.get(rect.w, rect.h, radius)

    def _cover_scale_to_surface(self, src: pygame.Surface, w: int, h: int) -> pygame.Surface:
        """이미지를 화면/카드 크기에 꽉 차게 center-crop."""
        sw, sh = src.get_size()
        if sw <= 0 or sh <= 0:
            out = pygame.Surface((w, h)).convert()
            self.gradient_fill(out, self.DARK_PURPLE, self.DARK_BLUE)
            return out
        scale = max(w / sw, h / sh)
        nw, nh = max(1, int(sw * scale)), max(1, int(sh * scale))
        scaled = pygame.transform.smoothscale(src, (nw, nh))
        out = pygame.Surface((w, h)).convert()
        out.blit(scaled, ((w - nw) // 2, (h - nh) // 2))
        return out

    def _render_modern_background(self):
        """업로드한 성운 배경 이미지를 메뉴 배경으로 사용.

        배경 경로: data/images/menu/background_nebula.png
        이미지가 없으면 조용한 다크 네이비 그라디언트로 대체된다.
        """
        try:
            raw = pygame.image.load(asset_path(MENU_BACKGROUND_IMAGE)).convert()
            bg = self._cover_scale_to_surface(raw, self.width, self.height)
        except Exception:
            bg = pygame.Surface((self.width, self.height)).convert()
            self.gradient_fill(bg, self.DARK_PURPLE, self.DARK_BLUE)

        # 배경 자체가 예쁘므로, UI 가독성을 위한 얇은 필름만 올린다.
        dim = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 26))
        bg.blit(dim, (0, 0))

        # 타이틀/카드가 있는 왼쪽과 아래쪽만 살짝 눌러서 텍스트가 뜨지 않게 함.
        left_shade = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        for x in range(self.width):
            t = x / max(1, self.width - 1)
            a = int(42 * ((1 - t) ** 2.2))
            pygame.draw.line(left_shade, (0, 0, 0, a), (x, 0), (x, self.height))
        bg.blit(left_shade, (0, 0))

        bottom_shade = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        for y in range(self.height):
            t = y / max(1, self.height - 1)
            a = int(58 * (t ** 2.0))
            pygame.draw.line(bottom_shade, (0, 2, 10, a), (0, y), (self.width, y))
        bg.blit(bottom_shade, (0, 0))

        # 아주 약한 vignette. 화면 가장자리만 정리하고, 중앙 배경은 보존한다.
        vignette = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        cx, cy = self.width * 0.50, self.height * 0.48
        max_d = math.hypot(max(cx, self.width - cx), max(cy, self.height - cy))
        step = 5
        for y in range(0, self.height, step):
            for x in range(0, self.width, step):
                d = math.hypot(x + step / 2 - cx, y + step / 2 - cy) / max_d
                a = int(48 * max(0.0, d - 0.45) ** 1.8)
                if a > 0:
                    pygame.draw.rect(vignette, (0, 0, 0, a), (x, y, step, step))
        bg.blit(vignette, (0, 0))
        return bg.convert()

    def gradient_fill(self, screen, color_top, color_bottom):
        w, h = screen.get_size()
        # 고정 배경 외엔 작은 영역에만 사용됨 → 여전히 빠름
        for y in range(h):
            r = int(color_top[0] + (color_bottom[0] - color_top[0]) * (y / (h-1)))
            g = int(color_top[1] + (color_bottom[1] - color_top[1]) * (y / (h-1)))
            b = int(color_top[2] + (color_bottom[2] - color_top[2]) * (y / (h-1)))
            pygame.draw.line(screen, (r, g, b), (0, y), (w, y))

    def _shine(self, target, t):
        if t <= 0 or t >= 1: return
        w, h = target.get_size()
        band_w = int(max(10, w * 0.10))
        grad = pygame.Surface((band_w, h*2), pygame.SRCALPHA)
        for x in range(band_w):
            a = int(120 * (1 - abs((x - band_w/2) / (band_w/2))))
            pygame.draw.line(grad, (255, 255, 255, a), (x, 0), (x, h*2))
        grad = pygame.transform.rotate(grad, -25)
        pos_x = int(lerp(-w, w*1.2, t))
        rect = grad.get_rect(center=(pos_x, h//2))
        target.blit(grad, rect)

    # -------------------------- Precompute tiles ----------------------------
    def _precompute_tile_assets(self):
        """타일 크기 및 hover 크기별로 이미지/패턴/그라디언트 등을 프리컴퓨트."""
        for i, base in enumerate(self.tile_rects):
            tile = self.tiles[i]
            radius = 26 if i == 0 else 22
            for scale in (1.0, 1.025):
                w = int(base.w * scale)
                h = int(base.h * scale)
                key = (i, w, h)
                if key in self._tile_assets:
                    continue

                visual = self._tile_visual_cache.get(
                    tile.get("image"),
                    w,
                    h,
                    radius,
                    tile.get("fallback_color", MODERN_PANEL),
                )

                gap = max(18, int(w * PATTERN_GAP_K))
                frames = self._pattern_frames_cache.build_frames(
                    w, h, radius, gap, PATTERN_ANGLE, PATTERN_ALPHA, PATTERN_FRAMES
                )
                grad_overlay = self._grad_overlay_cache.get(w, h, radius)
                self._tile_assets[key] = {
                    "radius": radius,
                    "visual": visual,
                    "frames": frames,
                    "grad": grad_overlay,
                }

    # --------------------------------- Draw ---------------------------------
    def _draw_scrollbar(self, screen):
        if self.max_scroll_x <= 1:
            return
        track_w = int(self.width * 0.46)
        track_h = 6
        track_x = (self.width - track_w) // 2
        track_y = int(self.height * 0.90)

        bar = pygame.Surface((track_w, track_h), pygame.SRCALPHA)
        TRACK_RGBA = (210, 225, 245, 16)
        KNOB_RGBA  = (145, 170, 210, 125)
        pygame.draw.rect(bar, TRACK_RGBA, (0, 0, track_w, track_h), border_radius=track_h//2)

        content_w = getattr(self, "content_width", self.max_scroll_x + self.width)
        view_w = self.width
        knob_w = max(40, int(track_w * (view_w / max(content_w, 1))))

        p = 0.0 if self.max_scroll_x <= 0 else (self.scroll_x / self.max_scroll_x)
        p = max(0.0, min(1.0, p))
        knob_x = int((track_w - knob_w) * p)
        pygame.draw.rect(bar, KNOB_RGBA, (knob_x, 0, knob_w, track_h), border_radius=track_h//2)
        screen.blit(bar, (track_x, track_y))

    def draw_tiles(self, screen):
        mouse = pygame.mouse.get_pos()
        self.hovered_tile_index = None

        view_l = self.scroll_x - 100
        view_r = self.scroll_x + self.width + 100

        for i, tile in enumerate(self.tiles):
            base = self.tile_rects[i]
            if base.right < view_l or base.left > view_r:
                continue

            rect = base.move(-int(self.scroll_x), 0)
            hovered = (self.modal is None) and rect.collidepoint(mouse)
            if hovered:
                # 너무 튀는 확대감 제거. 약간만 커지게 함.
                w = int(rect.w * 1.025); h = int(rect.h * 1.025)
                rect = pygame.Rect(0, 0, w, h).move(rect.centerx - w//2, rect.centery - h//2)

            key = (i, rect.w, rect.h)
            assets = self._tile_assets[key]
            radius = assets["radius"]

            # 버튼 주변 그림자/글로우 제거. 배경 이미지와 겹칠 때 지저분해 보이지 않게
            # 카드 자체만 깔끔하게 그림.

            # 이미지 버튼 본체. 이미지가 없으면 fallback_color 단색 배경.
            visual: pygame.Surface = assets["visual"]
            screen.blit(visual, rect.topleft)

            # 상단 유리광만 아주 약하게. 줄무늬/네온/화살표는 제거.
            grad = assets["grad"]
            screen.blit(grad, rect.topleft)

            # Hover는 글로우 없이 얇은 테두리만 표시.
            if hovered:
                pygame.draw.rect(screen, (170, 190, 220), rect, width=2, border_radius=radius)
                self.hovered_tile_index = i

            # 텍스트: 이미지 버튼 하단 라벨.
            pad_x = max(16, rect.w // 16)
            pad_y = max(14, rect.h // 10)

            eyebrow_surf = self._tile_eyebrow_surf[i]
            title_surf = self._tile_title_surf[i]

            eyebrow_rect = eyebrow_surf.get_rect(
                left=rect.left + pad_x,
                bottom=rect.bottom - pad_y - title_surf.get_height() + 2
            )
            title_rect = title_surf.get_rect(
                left=rect.left + pad_x,
                bottom=rect.bottom - pad_y
            )
            screen.blit(eyebrow_surf, eyebrow_rect)
            screen.blit(title_surf, title_rect)

        # 상단 타이틀
        screen.blit(self.title_text_surface, self.title_text_pos)
        screen.blit(self.small_title_text_surface, self.small_title_pos)

        self._draw_scrollbar(screen)

        # 모달 열려 있으면 그리기
        if self.modal is not None:
            self.modal.draw(screen)

    # ------------------------------- Input ----------------------------------
    def _open_confirm_modal(self, title):
        if title.lower().startswith("how"):
            mtitle = "Proceed to How To?"
            msg = "Open How To now."
            yes = "Yes"
        else:
            mtitle = f"Play {title}?"
            msg = "Start the game now."
            yes = "Yes"
        self.modal = ModalDialog(self, mtitle, msg, yes_text=yes, cancel_text="Cancel")
        self.pending_select_title = title

    def handle_mouse(self, event):
        if self.modal is not None:
            self.modal.handle_event(event)
            return None

        now = pygame.time.get_ticks() / 1000.0
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.inertia_v = 0.0  # stop inertia on new drag
            self.mouse_down = True
            self.dragging = True
            self.drag_start_x = pygame.mouse.get_pos()[0]
            self.scroll_start_x = self.scroll_x
            self.total_drag = 0.0
            self._vel_samples.clear()
            self._vel_samples.append((now, self.drag_start_x))

        elif event.type == pygame.MOUSEMOTION and self.dragging and self.mouse_down:
            x = pygame.mouse.get_pos()[0]
            dx = x - self.drag_start_x
            self.scroll_x = self.scroll_start_x - dx
            self.scroll_x = max(0, min(self.scroll_x, self.max_scroll_x))
            self.total_drag += abs(dx)
            self._vel_samples.append((now, x))

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.mouse_down = False
            was_drag = self.total_drag > 6
            self.dragging = False

            if not was_drag:
                mouse_pos = pygame.mouse.get_pos()
                for i, base in enumerate(self.tile_rects):
                    rect = base.move(-int(self.scroll_x), 0)
                    if rect.collidepoint(mouse_pos):
                        self._open_confirm_modal(self.tiles[i]["title"])
                        return None

            # 관성 계산
            vx_mouse = 0.0
            if len(self._vel_samples) >= 2:
                t0, x0 = self._vel_samples[0]
                t1, x1 = self._vel_samples[-1]
                dt = max(1e-4, t1 - t0)
                vx_mouse = (x1 - x0) / dt  # px/sec
            v_scroll = -vx_mouse  # 스크롤 좌표계는 반대
            if was_drag and abs(v_scroll) > 220:  # 임계속도 (살살 드래그는 스냅/관성 억제)
                self.inertia_v = v_scroll
                self.snap_target_x = None
            else:
                # 느린 드래그: 방향에 맞는 앵커가 가깝게 있을 때만 스냅 (역방향 미세 이동 방지)
                if self.anchors:
                    cur = self.scroll_x
                    dir_sign = 1 if vx_mouse > 0 else (-1 if vx_mouse < 0 else 0)
                    self._last_drag_dir = dir_sign if was_drag else 0
                    target = None
                    if dir_sign > 0:
                        forward = min((a for a in self.anchors if a >= cur), default=None)
                        if forward is not None and abs(forward - cur) <= 18:
                            target = forward
                    elif dir_sign < 0:
                        backward = max((a for a in self.anchors if a <= cur), default=None)
                        if backward is not None and abs(backward - cur) <= 18:
                            target = backward
                    else:
                        near = min(self.anchors, key=lambda a: abs(a - cur))
                        if abs(near - cur) <= 12:
                            target = near
                    self.snap_target_x = target

        elif event.type == pygame.MOUSEWHEEL:
            self.inertia_v = 0.0
            self.snap_target_x = None
            self.scroll_x -= event.y * 60
            self.scroll_x = max(0, min(self.scroll_x, self.max_scroll_x))

        elif event.type == pygame.KEYDOWN:
            self.inertia_v = 0.0
            if self.anchors:
                if event.key in (pygame.K_RIGHT, pygame.K_d):
                    nxt = min(self.anchors[-1], min((a for a in self.anchors if a > self.scroll_x + 1), default=self.anchors[-1]))
                    self.snap_target_x = nxt
                elif event.key in (pygame.K_LEFT, pygame.K_a):
                    prv = max(0.0, max((a for a in self.anchors if a < self.scroll_x - 1), default=0.0))
                    self.snap_target_x = prv

    # ------------------------------ Squares ---------------------------------
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

    # --------------------------------- Loop ---------------------------------
    def loop(self, screen):
        clock = pygame.time.Clock()
        running = True
        frame_cnt = 0

        while running:
            dt_ms = clock.tick(60)
            dt = dt_ms / 1000.0

            self.frame_count += 1
            # clean 버전: 배경 장식 애니메이션은 사용하지 않음.

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if frame_cnt > 10:
                    if self.modal is not None:
                        self.modal.handle_event(event)
                    else:
                        self.handle_mouse(event)

            # 모달 결과
            if self.modal is not None and self.modal.result is not None:
                if self.modal.result is True and self.pending_select_title:
                    return self.pending_select_title, screen
                self.modal = None
                self.pending_select_title = None

            # Inertia update (관성)
            if self.modal is None and not self.dragging and abs(self.inertia_v) > 0:
                # 스냅 중지 후 관성 우선
                self.snap_target_x = None
                self.scroll_x += self.inertia_v * dt
                # 마찰 감속
                decel = 2500.0
                if self.inertia_v > 0:
                    self.inertia_v = max(0.0, self.inertia_v - decel * dt)
                else:
                    self.inertia_v = min(0.0, self.inertia_v + decel * dt)
                # 경계 처리
                if self.scroll_x < 0:
                    self.scroll_x = 0
                    self.inertia_v = 0.0
                elif self.scroll_x > self.max_scroll_x:
                    self.scroll_x = self.max_scroll_x
                    self.inertia_v = 0.0
                # 멈추면 스냅 (가까운 경우에만, 방향 고려)
                if abs(self.inertia_v) < 1.0:
                    self.inertia_v = 0.0
                    if self.anchors:
                        cur = self.scroll_x
                        target = None
                        if self._last_drag_dir > 0:
                            forward = min((a for a in self.anchors if a >= cur), default=None)
                            if forward is not None and abs(forward - cur) <= 18:
                                target = forward
                        elif self._last_drag_dir < 0:
                            backward = max((a for a in self.anchors if a <= cur), default=None)
                            if backward is not None and abs(backward - cur) <= 18:
                                target = backward
                        else:
                            near = min(self.anchors, key=lambda a: abs(a - cur))
                            if abs(near - cur) <= 12:
                                target = near
                        self.snap_target_x = target

            # 스냅 보간 (관성이 없을 때만)
            if self.modal is None and self.snap_target_x is not None and not self.dragging and self.inertia_v == 0.0:
                self.scroll_x = lerp(self.scroll_x, self.snap_target_x, min(10.0 * dt, 1.0))
                if abs(self.scroll_x - self.snap_target_x) < 0.5:
                    self.scroll_x = self.snap_target_x
                    self.snap_target_x = None

            # Background (프리렌더된 그라디언트 사용)
            screen.blit(self._bg, (0, 0))

            # Tiles (+ 모달)
            self.draw_tiles(screen)

            if self.show_fps:
                blit_fps(screen, clock)

            pygame.display.flip()
            frame_cnt += 1

# ------------------------------- Run ---------------------------------------
if __name__ == "__main__":
    WIDTH, HEIGHT = 1280, 720
    # 하드웨어 더블버퍼 & vsync (가능한 경우) → 안정된 프레임
    try:
        screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.SCALED | pygame.DOUBLEBUF, vsync=1)
    except TypeError:
        # pygame < 2.0 또는 플랫폼 미지원 시 폴백
        screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("PlayCoreMenu — Nebula Image Cards")

    menu_screen = PlayCoreMenu(WIDTH, HEIGHT, show_fps=True)
    print(menu_screen.loop(screen))
