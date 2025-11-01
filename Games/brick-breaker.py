import pygame
import random

# Initialize Pygame
pygame.init()

# Screen settings
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Brick Breaker")

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
BLUE = (0, 0, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)

# Game objects
PADDLE_WIDTH, PADDLE_HEIGHT = 100, 10
BALL_RADIUS = 10
BRICK_WIDTH, BRICK_HEIGHT = 75, 20

# Paddle
paddle = pygame.Rect(WIDTH//2 - PADDLE_WIDTH//2, HEIGHT - 40, PADDLE_WIDTH, PADDLE_HEIGHT)

# Ball
ball = pygame.Rect(WIDTH//2, HEIGHT//2, BALL_RADIUS*2, BALL_RADIUS*2)
ball_dx = 4
ball_dy = -4

# Bricks
bricks = []
rows, cols = 5, 10
for row in range(rows):
    for col in range(cols):
        brick = pygame.Rect(col * (BRICK_WIDTH + 10) + 35, row * (BRICK_HEIGHT + 10) + 50, BRICK_WIDTH, BRICK_HEIGHT)
        bricks.append(brick)

# Clock
clock = pygame.time.Clock()
font = pygame.font.SysFont(None, 36)

def draw():
    screen.fill(BLACK)
    pygame.draw.rect(screen, BLUE, paddle)
    pygame.draw.ellipse(screen, WHITE, ball)

    for brick in bricks:
        pygame.draw.rect(screen, RED, brick)

    if not game_active:
        text = font.render("Game Over! Press R to Restart", True, GREEN)
        screen.blit(text, (WIDTH//2 - text.get_width()//2, HEIGHT//2))

    pygame.display.flip()

def reset_game():
    global ball, ball_dx, ball_dy, bricks, paddle, game_active
    ball = pygame.Rect(WIDTH//2, HEIGHT//2, BALL_RADIUS*2, BALL_RADIUS*2)
    ball_dx = 4 * random.choice([-1, 1])
    ball_dy = -4
    paddle.x = WIDTH//2 - PADDLE_WIDTH//2
    bricks.clear()
    for row in range(rows):
        for col in range(cols):
            brick = pygame.Rect(col * (BRICK_WIDTH + 10) + 35, row * (BRICK_HEIGHT + 10) + 50, BRICK_WIDTH, BRICK_HEIGHT)
            bricks.append(brick)
    game_active = True

# Main loop
game_active = True
running = True
while running:
    clock.tick(60)
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    keys = pygame.key.get_pressed()

    if keys[pygame.K_LEFT] and paddle.left > 0:
        paddle.x -= 7
    if keys[pygame.K_RIGHT] and paddle.right < WIDTH:
        paddle.x += 7
    if keys[pygame.K_r] and not game_active:
        reset_game()

    if game_active:
        ball.x += ball_dx
        ball.y += ball_dy

        # Collisions
        if ball.left <= 0 or ball.right >= WIDTH:
            ball_dx *= -1
        if ball.top <= 0:
            ball_dy *= -1
        if ball.colliderect(paddle):
            ball_dy *= -1

        hit_index = ball.collidelist(bricks)
        if hit_index != -1:
            del bricks[hit_index]
            ball_dy *= -1

        if ball.bottom >= HEIGHT:
            game_active = False

    draw()

pygame.quit()
