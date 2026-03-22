import math
import pygame
import random

colors = [
    (0, 0, 0),
    (155, 92, 255),
    (90, 240, 255),
    (255, 145, 90),
    (120, 255, 150),
    (255, 90, 125),
    (255, 210, 70),
]

SCREEN_WIDTH = 700
SCREEN_HEIGHT = 540
FIELD_OFFSET_X = 110
FIELD_OFFSET_Y = 70
BLOCK_SIZE = 22
PREVIEW_OFFSET_X = 410
PANEL_WIDTH = 220
LINE_SCORES = [0, 100, 300, 500, 800]

BACKGROUND_TOP = (8, 14, 34)
BACKGROUND_BOTTOM = (2, 5, 16)
GRID_LINE = (40, 90, 140)
PANEL_BG = (10, 20, 44)
PANEL_EDGE = (60, 160, 255)
TEXT_PRIMARY = (220, 240, 255)
TEXT_SECONDARY = (120, 180, 255)
GLOW_COLOR = (0, 220, 255)
GHOST_ALPHA = 85


def clamp_color(value):
    return max(0, min(255, int(value)))


def blend(color_a, color_b, amount):
    return tuple(
        clamp_color(color_a[i] + (color_b[i] - color_a[i]) * amount)
        for i in range(3)
    )


def lighten(color, amount):
    return blend(color, (255, 255, 255), amount)


def darken(color, amount):
    return blend(color, (0, 0, 0), amount)


class Figure:
    x = 0
    y = 0

    figures = [
        [[1, 5, 9, 13], [4, 5, 6, 7]],
        [[4, 5, 9, 10], [2, 6, 5, 9]],
        [[6, 7, 9, 10], [1, 5, 6, 10]],
        [[1, 2, 5, 9], [0, 4, 5, 6], [1, 5, 9, 8], [4, 5, 6, 10]],
        [[1, 2, 6, 10], [5, 6, 7, 9], [2, 6, 10, 11], [3, 5, 6, 7]],
        [[1, 4, 5, 6], [1, 4, 5, 9], [4, 5, 6, 9], [1, 5, 6, 9]],
        [[1, 2, 5, 6]],
    ]

    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.type = random.randint(0, len(self.figures) - 1)
        self.color = random.randint(1, len(colors) - 1)
        self.rotation = 0

    def image(self):
        return self.figures[self.type][self.rotation]

    def rotate(self):
        self.rotation = (self.rotation + 1) % len(self.figures[self.type])


class Tetris:
    def __init__(self, height, width):
        self.level = 2
        self.score = 0
        self.lines = 0
        self.state = "start"
        self.height = height
        self.width = width
        self.x = FIELD_OFFSET_X
        self.y = FIELD_OFFSET_Y
        self.zoom = BLOCK_SIZE
        self.figure = None
        self.next_figure = Figure(3, 0)
        self.field = [[0 for _ in range(width)] for _ in range(height)]

    def new_figure(self):
        self.figure = self.next_figure
        self.figure.x = 3
        self.figure.y = 0
        self.next_figure = Figure(3, 0)

    def intersects(self):
        return self.intersects_at(self.figure.x, self.figure.y, self.figure.rotation)

    def intersects_at(self, x, y, rotation):
        for i in range(4):
            for j in range(4):
                if i * 4 + j in self.figure.figures[self.figure.type][rotation]:
                    if (
                        i + y > self.height - 1
                        or j + x > self.width - 1
                        or j + x < 0
                        or self.field[i + y][j + x] > 0
                    ):
                        return True
        return False

    def break_lines(self):
        lines = 0
        for i in range(1, self.height):
            if all(self.field[i][j] > 0 for j in range(self.width)):
                lines += 1
                for i1 in range(i, 0, -1):
                    for j in range(self.width):
                        self.field[i1][j] = self.field[i1 - 1][j]
                for j in range(self.width):
                    self.field[0][j] = 0
        self.lines += lines
        self.score += LINE_SCORES[min(lines, 4)] * self.level

    def get_ghost_y(self):
        if self.figure is None:
            return 0
        ghost_y = self.figure.y
        while not self.intersects_at(self.figure.x, ghost_y + 1, self.figure.rotation):
            ghost_y += 1
        return ghost_y

    def go_space(self):
        if self.figure is None:
            return
        self.figure.y = self.get_ghost_y()
        self.freeze()

    def go_down(self):
        self.figure.y += 1
        if self.intersects():
            self.figure.y -= 1
            self.freeze()

    def freeze(self):
        for i in range(4):
            for j in range(4):
                if i * 4 + j in self.figure.image():
                    self.field[i + self.figure.y][j + self.figure.x] = self.figure.color
        self.break_lines()
        self.new_figure()
        if self.intersects():
            self.state = "gameover"

    def go_side(self, dx):
        old_x = self.figure.x
        self.figure.x += dx
        if self.intersects():
            self.figure.x = old_x

    def rotate(self):
        old_rotation = self.figure.rotation
        self.figure.rotate()
        if self.intersects():
            self.figure.rotation = old_rotation


def draw_vertical_gradient(surface, top_color, bottom_color):
    height = surface.get_height()
    width = surface.get_width()
    for y in range(height):
        ratio = y / max(1, height - 1)
        color = blend(top_color, bottom_color, ratio)
        pygame.draw.line(surface, color, (0, y), (width, y))


def draw_starfield(surface, stars, tick):
    for index, (x, y, radius, speed) in enumerate(stars):
        twinkle = 0.5 + 0.5 * math.sin((tick * speed) + index)
        color = (
            clamp_color(80 + 120 * twinkle),
            clamp_color(120 + 100 * twinkle),
            255,
        )
        pygame.draw.circle(surface, color, (x, y), radius)


def draw_glow(surface, rect, color, alpha, expand=12, border_radius=18):
    glow_surface = pygame.Surface((rect.width + expand * 2, rect.height + expand * 2), pygame.SRCALPHA)
    glow_color = (*color, alpha)
    pygame.draw.rect(
        glow_surface,
        glow_color,
        (expand, expand, rect.width, rect.height),
        border_radius=border_radius,
    )
    surface.blit(glow_surface, (rect.x - expand, rect.y - expand), special_flags=pygame.BLEND_RGBA_ADD)


def draw_panel(surface, rect):
    draw_glow(surface, rect, PANEL_EDGE, 55, expand=16, border_radius=24)
    panel_surface = pygame.Surface(rect.size, pygame.SRCALPHA)
    panel_surface.fill((*PANEL_BG, 230))
    pygame.draw.rect(panel_surface, (*lighten(PANEL_EDGE, 0.1), 220), panel_surface.get_rect(), width=2, border_radius=22)
    surface.blit(panel_surface, rect.topleft)


def draw_block(surface, color, bx, by, size, ghost=False):
    block_rect = pygame.Rect(bx, by, size - 1, size - 1)
    top = lighten(color, 0.45)
    face = color
    side = darken(color, 0.28)
    shadow = darken(color, 0.5)

    alpha = GHOST_ALPHA if ghost else 255
    block_surface = pygame.Surface((size + 10, size + 10), pygame.SRCALPHA)

    pygame.draw.polygon(
        block_surface,
        (*shadow, int(alpha * 0.35)),
        [(10, size - 2), (size + 3, size - 2), (size - 2, size + 4), (4, size + 4)],
    )
    pygame.draw.polygon(
        block_surface,
        (*top, alpha),
        [(6, 2), (size - 3, 2), (size + 2, 8), (10, 8)],
    )
    pygame.draw.polygon(
        block_surface,
        (*side, alpha),
        [(size - 3, 2), (size + 2, 8), (size + 2, size - 1), (size - 3, size - 7)],
    )
    pygame.draw.rect(block_surface, (*face, alpha), (4, 8, size - 8, size - 10), border_radius=5)
    pygame.draw.rect(block_surface, (*lighten(color, 0.65), int(alpha * 0.95)), (7, 11, size - 20, 4), border_radius=2)
    pygame.draw.rect(block_surface, (*darken(color, 0.6), int(alpha * 0.5)), (8, size - 12, size - 18, 3), border_radius=2)

    if not ghost:
        draw_glow(surface, block_rect.inflate(2, 2), color, 40, expand=8, border_radius=10)
    surface.blit(block_surface, (bx - 4, by - 4))


def draw_board(surface, game, pulse):
    board_rect = pygame.Rect(game.x - 16, game.y - 20, game.zoom * game.width + 32, game.zoom * game.height + 40)
    draw_glow(surface, board_rect, GLOW_COLOR, 60 + int(15 * pulse), expand=20, border_radius=26)
    board_surface = pygame.Surface(board_rect.size, pygame.SRCALPHA)
    pygame.draw.rect(board_surface, (4, 14, 34, 235), board_surface.get_rect(), border_radius=24)
    pygame.draw.rect(board_surface, (70, 180, 255, 180), board_surface.get_rect(), width=2, border_radius=24)
    surface.blit(board_surface, board_rect.topleft)

    field_rect = pygame.Rect(game.x, game.y, game.zoom * game.width, game.zoom * game.height)
    field_surface = pygame.Surface(field_rect.size, pygame.SRCALPHA)
    draw_vertical_gradient(field_surface, (18, 30, 70), (5, 12, 28))
    for row in range(game.height + 1):
        pygame.draw.line(field_surface, GRID_LINE, (0, row * game.zoom), (field_rect.width, row * game.zoom), 1)
    for col in range(game.width + 1):
        pygame.draw.line(field_surface, GRID_LINE, (col * game.zoom, 0), (col * game.zoom, field_rect.height), 1)
    surface.blit(field_surface, field_rect.topleft)


def draw_piece(surface, figure, color_index, offset_x, offset_y, block_size):
    for i in range(4):
        for j in range(4):
            if i * 4 + j in figure.image():
                bx = offset_x + j * block_size
                by = offset_y + i * block_size
                draw_block(surface, colors[color_index], bx, by, block_size)


def draw_preview(surface, game, font_small, font_medium):
    preview_rect = pygame.Rect(PREVIEW_OFFSET_X, 70, PANEL_WIDTH, 165)
    stats_rect = pygame.Rect(PREVIEW_OFFSET_X, 255, PANEL_WIDTH, 210)
    draw_panel(surface, preview_rect)
    draw_panel(surface, stats_rect)

    surface.blit(font_medium.render("NEXT", True, TEXT_SECONDARY), (preview_rect.x + 18, preview_rect.y + 16))
    preview_figure = game.next_figure
    for i in range(4):
        for j in range(4):
            if i * 4 + j in preview_figure.image():
                bx = preview_rect.x + 42 + j * 28
                by = preview_rect.y + 54 + i * 28
                draw_block(surface, colors[preview_figure.color], bx, by, 26)

    labels = [
        ("SCORE", str(game.score)),
        ("LINES", str(game.lines)),
        ("LEVEL", str(game.level)),
    ]
    for index, (label, value) in enumerate(labels):
        label_y = stats_rect.y + 24 + index * 58
        surface.blit(font_small.render(label, True, TEXT_SECONDARY), (stats_rect.x + 18, label_y))
        surface.blit(font_medium.render(value, True, TEXT_PRIMARY), (stats_rect.x + 18, label_y + 20))

    tip_lines = ["↑ rotate", "← → move", "↓ boost", "space drop", "esc restart"]
    for idx, text in enumerate(tip_lines):
        surface.blit(
            font_small.render(text, True, lighten(TEXT_SECONDARY, 0.08)),
            (stats_rect.x + 118, stats_rect.y + 20 + idx * 32),
        )


def draw_game_over(surface, font_large, font_small):
    overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 8, 20, 140))
    surface.blit(overlay, (0, 0))
    card = pygame.Rect(150, 185, 400, 135)
    draw_panel(surface, card)
    surface.blit(font_large.render("SYSTEM FAILURE", True, (255, 130, 160)), (card.x + 34, card.y + 28))
    surface.blit(font_small.render("Press ESC to relaunch the grid", True, TEXT_PRIMARY), (card.x + 72, card.y + 82))


pygame.init()
pygame.display.set_caption("Neon Tetris")
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
clock = pygame.time.Clock()
fps = 25

font_small = pygame.font.SysFont("Consolas", 20, True, False)
font_medium = pygame.font.SysFont("Consolas", 32, True, False)
font_large = pygame.font.SysFont("Consolas", 40, True, False)

game = Tetris(20, 10)
done = False
counter = 0
pressing_down = False
stars = [
    (
        random.randint(0, SCREEN_WIDTH),
        random.randint(0, SCREEN_HEIGHT),
        random.randint(1, 2),
        random.uniform(0.015, 0.05),
    )
    for _ in range(70)
]

while not done:
    if game.figure is None:
        game.new_figure()

    counter += 1
    if counter > 100000:
        counter = 0

    if counter % max(1, (fps // game.level)) == 0 or pressing_down:
        if game.state == "start":
            game.go_down()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            done = True
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP and game.state == "start":
                game.rotate()
            if event.key == pygame.K_DOWN:
                pressing_down = True
            if event.key == pygame.K_LEFT and game.state == "start":
                game.go_side(-1)
            if event.key == pygame.K_RIGHT and game.state == "start":
                game.go_side(1)
            if event.key == pygame.K_SPACE and game.state == "start":
                game.go_space()
            if event.key == pygame.K_ESCAPE:
                game = Tetris(20, 10)
                pressing_down = False
        if event.type == pygame.KEYUP and event.key == pygame.K_DOWN:
            pressing_down = False

    pulse = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() * 0.005)
    draw_vertical_gradient(screen, BACKGROUND_TOP, BACKGROUND_BOTTOM)
    draw_starfield(screen, stars, pygame.time.get_ticks())

    title = font_large.render("TETRIS // FUTURE GRID", True, TEXT_PRIMARY)
    subtitle = font_small.render("Stack clean lines inside a holographic arena", True, TEXT_SECONDARY)
    screen.blit(title, (34, 18))
    screen.blit(subtitle, (36, 52))

    draw_board(screen, game, pulse)

    for i in range(game.height):
        for j in range(game.width):
            if game.field[i][j] > 0:
                bx = game.x + game.zoom * j + 1
                by = game.y + game.zoom * i + 1
                draw_block(screen, colors[game.field[i][j]], bx, by, game.zoom - 1)

    if game.figure is not None:
        ghost_y = game.get_ghost_y()
        for i in range(4):
            for j in range(4):
                p = i * 4 + j
                if p in game.figure.image():
                    bx = game.x + game.zoom * (j + game.figure.x) + 1
                    by = game.y + game.zoom * (i + ghost_y) + 1
                    draw_block(screen, colors[game.figure.color], bx, by, game.zoom - 1, ghost=True)
        draw_piece(screen, game.figure, game.figure.color, game.x + game.zoom * game.figure.x + 1, game.y + game.zoom * game.figure.y + 1, game.zoom - 1)

    draw_preview(screen, game, font_small, font_medium)

    if game.state == "gameover":
        draw_game_over(screen, font_large, font_small)

    pygame.display.flip()
    clock.tick(fps)

pygame.quit()
