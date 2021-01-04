import pygame as pg
import math
from random import randint
import os
import neat
import pygame_gui as pgui
import time

pg.init()

WW, WH = 1280, 720
SW, SH = 1500, 1000

window = pg.display.set_mode((WW, WH))
ui_manager = pgui.UIManager((WW, WH))
pg.display.set_caption("A.I. Learns to Drive in Turkish Grand Prix")
default_font = pg.font.SysFont(None, 24)
small_font = pg.font.SysFont(None, 20)
large_font = pg.font.SysFont(None, 30)

fonts = [small_font, default_font, large_font]

canvas = pg.Surface((SW, SH))
canvas.fill(pg.Color("white"))
mouse_pos = [0, 0]
FPS = 60
clock = pg.time.Clock()
game_level = 1
camera_pos = [0, 0]
record_time = -1
last_gen_best_time = -1
generation_count = 0
all_prev_fitness_avg = []

show_collision_lines = False
show_rays = False
camera_on = True
show_stats = True
show_graph = True
testing = False
testing_flag = False
paused = False
pause_screen_drawn = False

menu_banner = pg.transform.smoothscale(pg.image.load("assets/menu_banner.png"), (200, 100))
menu_bg = pg.transform.smoothscale(pg.image.load("assets/menu_bg.png"), (200, 720))
istanbul_park = pg.transform.smoothscale(pg.image.load("assets/istanbulpark.png"), (1500, 1000))
car_w, car_h = 40, 40
car_images = [
    pg.transform.smoothscale(pg.image.load("assets/red_car.png"), (car_w, car_h)),
    pg.transform.smoothscale(pg.image.load("assets/green_car.png"), (car_w, car_h)),
    pg.transform.smoothscale(pg.image.load("assets/blue_car.png"), (car_w, car_h)),
    pg.transform.smoothscale(pg.image.load("assets/yellow_car.png"), (car_w, car_h))
]


def remap(val, low1, high1, low2, high2):
    old_range = (high1 - low1)
    new_range = (high2 - low2)
    new_val = (((val - low1) * new_range) / old_range) + low2
    return new_val


def calc_distance(x1, y1, x2, y2):
    b = (y2 - y1)**2
    a = (x2 - x1)**2
    return math.sqrt(a+b)


def import_map(map):
    map.clear()
    file = open("assets/race_track_one.txt", "r")
    contents = ""
    if file.mode == "r":
        contents = file.readlines()

    for line in contents:
        cord = line.rstrip().split(",")     # Coordinates
        map.append(Line(int(cord[0]), int(cord[1]), int(cord[2]), int(cord[3])))


def rotate_image(image, angle):
    image_rect = image.get_rect()
    rotated_image = pg.transform.rotate(image, angle)
    rotated_rect = image_rect.copy()
    rotated_rect.center = rotated_image.get_rect().center
    rotated_image = rotated_image.subsurface(rotated_rect).copy()
    return rotated_image


class Line(object):
    def __init__(self, x1, y1, x2, y2):
        self.x1, self.y1 = x1, y1
        self.x2, self.y2 = x2, y2

        self.p1 = [self.x1, self.y1]
        self.p2 = [self.x2, self.y2]

    def draw(self, canvas):
        pg.draw.line(canvas, pg.Color("black"), [self.x1, self.y1], [self.x2, self.y2], 5)

    def get_coordinates(self):
        return str(self.x1) + "," + str(self.y1) + "," + str(self.x2) + "," + str(self.y2)


class Ray(object):
    def __init__(self, x, y, angle, length=10000, width=1):
        self.length = length
        self.dist = 10000
        self.width = width
        self.x1 = x
        self.y1 = y
        self.p1 = [self.x1, self.y1]
        self.angle = angle
        self.p2 = self.calc_end_pos()
        self.act_p2 = self.calc_end_pos()

    def change_first_pos(self, new_pos):
        self.x1, self.y1 = new_pos[0], new_pos[1]
        self.p1 = [self.x1, self.y1]
        self.p2 = self.calc_end_pos()

    def calc_end_pos(self):
        r_angle = math.radians(self.angle)
        p2x = self.x1 + math.cos(r_angle) * self.length
        p2y = self.y1 - math.sin(r_angle) * self.length
        return [p2x, p2y]

    def change_angle(self, delta):
        self.angle = self.angle + delta
        self.p2 = self.calc_end_pos()

    def calculate_intersection(self, walls):
        intersecting_points = []
        x1, y1 = self.p1[0], self.p1[1]
        x2, y2 = self.p2[0], self.p2[1]
        for wall in walls:
            x3, y3 = wall.p1[0], wall.p1[1]
            x4, y4 = wall.p2[0], wall.p2[1]

            payda = ((x1 - x2)*(y3 - y4)) - ((y1 - y2)*(x3 - x4))
            if math.fabs(payda) < 0.01:
                continue
            else:
                t_pay = ((x1 - x3)*(y3 - y4))-((y1 - y3)*(x3 - x4))
                u_pay = -(((x1 - x2)*(y1 - y3))-((y1 - y2)*(x1 - x3)))

                t = t_pay / payda
                u = u_pay / payda
                if (0 <= u <= 1) and (0 <= t <= 1):
                    px = math.floor(x1 + t*(x2 - x1))
                    py = math.floor(y1 + t*(y2 - y1))
                    intersecting_points.append([px, py])

        return intersecting_points

    def draw(self, canvas, car_angle):
        ray_color = "green"
        if self.angle == car_angle:
            ray_color = "blue"
        pg.draw.line(canvas, pg.Color(ray_color), self.p1, self.act_p2, self.width)

    def closest_intersection(self, inter_points):
        min = 10000
        ipx, ipy = self.act_p2[0], self.act_p2[1]
        for point in inter_points:
            d = calc_distance(self.x1, self.y1, point[0], point[1])
            if d < min:
                min = d
                ipx, ipy = point[0], point[1]
                self.dist = d
        return [ipx, ipy]

    def update(self, walls):
        int_points = []
        int_points = self.calculate_intersection(walls)
        closest_int_p = self.closest_intersection(int_points)
        self.act_p2 = closest_int_p


def generate_line_from_two_points(p1, p2):
    return Line(p1[0], p1[1], p2[0], p2[1])


class Car(object):
    def __init__(self, pos, ray_count, angle, id):
        self.image_id = randint(0, len(car_images)-1)
        self.image = car_images[self.image_id]
        self.fitness_id = id
        self.alive = True
        self.has_won = False
        self.pos = pos
        self.angle = angle
        self.ray_count = ray_count
        self.rays = []
        self.generate_rays()
        self.rotate_all(math.radians(self.angle))

    def get_ray_distances(self):
        dists = []
        for ray in self.rays:
            dists.append(ray.dist)
        return dists

    def generate_rays(self):
        angle_step = 360 / self.ray_count
        temp_angle = 0
        for i in range(self.ray_count):
            self.rays.append(Ray(self.pos[0], self.pos[1], temp_angle + self.angle))
            temp_angle += angle_step

    def change_pos(self, new_pos):
        self.pos = new_pos
        for ray in self.rays:
            ray.change_first_pos(self.pos)

    def move_forward(self):
        new_x_pos = self.pos[0] + int(math.cos(math.radians(self.angle)) * 7)
        new_y_pos = self.pos[1] - int(math.sin(math.radians(self.angle)) * 7)
        self.change_pos([new_x_pos, new_y_pos])

    def movement(self, keys):
        if self.alive:
            if keys[pg.K_w] or keys[pg.K_UP]:
                self.move_forward()
            if keys[pg.K_d] or keys[pg.K_RIGHT]:
                self.rotate_all(-8)
            if keys[pg.K_a] or keys[pg.K_LEFT]:
                self.rotate_all(8)

    def rotate_all(self, delta):
        self.angle += delta
        for ray in self.rays:
            ray.change_angle(delta)

        self.image = rotate_image(car_images[self.image_id], self.angle)

    def check_for_crash(self, ray_distance):
        if ray_distance < 10:
            self.alive = False

    def check_for_win(self, finish_line):
        width = 20
        height = finish_line.y2 - finish_line.y1
        if pg.Rect(finish_line.x1, finish_line.y1, width, height).collidepoint(self.pos[0], self.pos[1]):
            self.has_won = True
        else:
            pass

    def draw(self, canvas, walls):
        if self.alive:
            for ray in self.rays:
                ray.update(walls)
                if show_rays:
                    ray.draw(canvas, self.angle)
                self.check_for_crash(ray.dist)

        car_pos = [self.pos[0] - car_w//2, self.pos[1] - car_h//2]
        canvas.blit(self.image, car_pos)
        return self.alive


def show_text(canvas, text, color, pos, size):
    msg = fonts[size-1].render(text, True, color)
    canvas.blit(msg, pos)


def draw_menu(canvas, alive_cars, record_time, last_gen_best_time, generation_count, all_prev_fitness_avg):
    menu_start_x = 1080
    menu_width = 200
    menu_height = SH

    pg.draw.rect(canvas, (200, 200, 200), (menu_start_x, 0, menu_width, menu_height))
    canvas.blit(menu_bg, (menu_start_x, 0))
    canvas.blit(menu_banner, (menu_start_x, 5))

    menu_color = (10, 10, 10)
    show_text(canvas, "Simulation", menu_color, (menu_start_x + 10, 120), 2)
    pg.draw.line(canvas, menu_color, (menu_start_x + 10, 140), (menu_start_x + 190, 140), 2)
    pg.draw.line(canvas, menu_color, (menu_start_x + 10, 300), (menu_start_x + 190, 300), 2)

    show_text(canvas, "User Interface", menu_color, (menu_start_x + 10, 330), 2)
    pg.draw.line(canvas, menu_color, (menu_start_x + 10, 350), (menu_start_x + 190, 350), 2)
    pg.draw.line(canvas, menu_color, (menu_start_x + 10, 560), (menu_start_x + 190, 560), 2)

    if show_stats:

        surface_w = 340 if show_graph else 320
        surface_h = 270 if show_graph else 140
        statistics_surface = pg.Surface((surface_w, surface_h))
        statistics_surface.set_alpha(80)
        pg.draw.rect(statistics_surface, (200, 200, 200), (0, 0, 400, 400))
        pg.draw.line(statistics_surface, (100, 100, 100), (10, 30), (surface_w-20, 30), 3)
        pg.draw.rect(statistics_surface, (10, 10, 20), (10, 160, 300, 100))
        canvas.blit(statistics_surface, (0, 0))

        show_text(canvas, "STATISTICS", pg.Color("black"), (10, 10), 2)
        show_text(canvas, "Generation count: " + str(generation_count), pg.Color("black"), (10, 40), 1)
        show_text(canvas, "Cars alive: " + str(len(alive_cars)), pg.Color("black"), (10, 60), 1)
        record_text = "Record Time: " + str(round(record_time, 2)) + " seconds" if record_time != -1 else "Record Time: NaN"
        show_text(canvas, record_text, pg.Color("black"), (10, 90), 1)
        last_gen_record_text = "Last Gen. Best Time: " + str(round(last_gen_best_time, 2)) + " seconds" if last_gen_best_time != -1 else "Last Gen. Best Time: NaN"
        show_text(canvas, last_gen_record_text, pg.Color("black"), (10, 110), 1)

        if show_graph:
            show_text(canvas, "Average Fitness Graph", pg.Color("black"), (10, 140), 1)
            upper_range = max(all_prev_fitness_avg)
            point_count = len(all_prev_fitness_avg)

            interval = int(295 / point_count)
            last_val = 170

            point_positions = [[312, 165]]

            if point_count == 1:
                y_val = int(remap(all_prev_fitness_avg[0], -2, upper_range, 260, 170))
                pg.draw.circle(canvas, pg.Color("white"), (20, y_val), 4)
            else:
                point_positions = []
                for i, avg in enumerate(all_prev_fitness_avg):
                    y_val = int(remap(avg, -2, upper_range, 260, 170))
                    if i == point_count - 1:
                        last_val = y_val
                    x_val = 20+interval*i

                    point_positions.append([x_val, y_val])
                    pg.draw.circle(canvas, pg.Color("white"), (x_val, y_val), 4)

            pg.draw.line(canvas, pg.Color("black"), (300, last_val-4), (310, last_val-4), 2)
            show_text(canvas, str(all_prev_fitness_avg[-1]), pg.Color("black"), (312, last_val-8), 1)

            for i in range(1, len(point_positions)):
                fx, fy = point_positions[i-1][0], point_positions[i-1][1]
                ex, ey = point_positions[i][0], point_positions[i][1]
                pg.draw.aaline(canvas, (255, 255, 255), (fx, fy), (ex, ey))


def pause_screen(canvas):
    transparent_surface = pg.Surface((1080, 720))
    transparent_surface.fill(pg.Color("black"))
    transparent_surface.set_alpha(100)
    canvas.blit(transparent_surface, (0, 0))
    show_text(canvas, "PAUSED", pg.Color("white"), (1080 // 2, 720 // 2), 3)
    pg.display.update()


def generate_ui():
    ui_manager.clear_and_reset()
    start_x = 1080
    lm = 10     # left margin

    pause_button = pgui.elements.UIButton(relative_rect=pg.Rect(start_x + lm, 150, 180, 40),
                                          text="Pause Toggle",
                                          manager=ui_manager, object_id="pause_button")

    reset_gen_button = pgui.elements.UIButton(relative_rect=pg.Rect(start_x + lm, 200, 180, 40),
                                              text="Next Generation",
                                              manager=ui_manager, object_id="reset_gen_button")

    reverse_track_button = pgui.elements.UIButton(relative_rect=pg.Rect(start_x + lm, 250, 180, 40),
                                                  text="Test The Species",
                                                  manager=ui_manager, object_id="reverse_track_button")

    camera_toggle_button = pgui.elements.UIButton(relative_rect=pg.Rect(start_x + lm, 360, 180, 40),
                                                  text="Camera Toggle",
                                                  manager=ui_manager, object_id="camera_toggle_button")
    rays_toggle_button = pgui.elements.UIButton(relative_rect=pg.Rect(start_x + lm, 410, 180, 40),
                                                text="Rays Toggle",
                                                manager=ui_manager, object_id="rays_toggle_button")

    graph_toggle_button = pgui.elements.UIButton(relative_rect=pg.Rect(start_x + lm, 460, 180, 40),
                                                 text="Graph Toggle",
                                                 manager=ui_manager, object_id="graph_toggle_button")

    stats_toggle_button = pgui.elements.UIButton(relative_rect=pg.Rect(start_x + lm, 510, 180, 40),
                                                 text="Stats Toggle",
                                                 manager=ui_manager, object_id="stats_toggle_button")


def main(genomes, config):
    global show_rays, show_collision_lines, mouse_pos, camera_on, camera_pos, testing, testing_flag, record_time
    global generation_count, last_gen_best_time, show_stats, show_graph, paused, pause_screen_drawn

    start_time = time.time()
    adjusted_current_time = time.time()
    generation_count += 1
    all_prev_fitness_avg.append(0)

    nets = []
    ge = []
    cars = []
    winner_cars = []
    winner_cars_finish_times = []
    all_fitness_values = []

    for i, g in genomes:
        net = neat.nn.FeedForwardNetwork.create(g, config)
        nets.append(net)
        start_angle = 180 if testing else 0
        cars.append(Car((540-randint(0, 40), 870-randint(0, 40)), 8, start_angle, (i-1)%25))
        g.fitness = 0
        all_fitness_values.append(0)
        ge.append(g)

    map = [
        Line(0, 0, 0, SH),
        Line(0, SH, SW, SH),
        Line(SW, SH, SW, 0),
        Line(SW, 0, 0, 0)
    ]

    if game_level == 1:
        import_map(map)

    finish_line = Line(580, 800, 580, 905)

    generate_ui()

    program = True
    while program:
        delta_time = clock.tick(FPS)/1000.0
        if not paused: adjusted_current_time += delta_time
        for event in pg.event.get():
            if event.type == pg.QUIT:
                program = False
                pg.quit()
                quit()
            if event.type == pg.MOUSEMOTION:
                mouse_pos = pg.mouse.get_pos()

            if event.type == pg.MOUSEBUTTONDOWN:
                if event.button == 1:
                    print(mouse_pos)

            if event.type == pg.KEYDOWN:
                if event.key == pg.K_i:
                    show_collision_lines = not show_collision_lines
                if event.key == pg.K_s:
                    show_rays = not show_rays
                if event.key == pg.K_c:
                    camera_on = not camera_on
                if event.key == pg.K_p:
                    paused = not paused

            if event.type == pg.USEREVENT:
                if event.user_type == pgui.UI_BUTTON_PRESSED:
                    if event.ui_object_id == "pause_button":
                        paused = not paused
                        pause_screen_drawn = False
                    if event.ui_object_id == "reset_gen_button":
                        for i, car in enumerate(cars):
                            car.alive = False
                    if event.ui_object_id == "camera_toggle_button":
                        camera_on = not camera_on
                    if event.ui_object_id == "rays_toggle_button":
                        show_rays = not show_rays
                    if event.ui_object_id == "reverse_track_button":
                        testing_flag = not testing_flag
                    if event.ui_object_id == "graph_toggle_button":
                        show_graph = not show_graph
                    if event.ui_object_id == "stats_toggle_button":
                        show_stats = not show_stats

            ui_manager.process_events(event)

        keys = pg.key.get_pressed()

        ui_manager.update(delta_time)

        if not paused:
            window.fill(pg.Color("black"))
            canvas.fill(pg.Color("black"))

            canvas.blit(istanbul_park, (0, 0))

            if show_collision_lines:
                for line in map:
                    line.draw(canvas)

            if len(cars) > 0:

                everyone_won = True
                for car in cars:
                    if not car.has_won:
                        everyone_won = False

                if everyone_won:
                    for car in cars:
                        car.alive = False

                for i, car in enumerate(cars):
                    car.move_forward()
                    alive = car.draw(canvas, map)
                    if not alive:
                        ge[i].fitness -= 3
                        cars.pop(i)
                        nets.pop(i)
                        ge.pop(i)
                    else:
                        ge[i].fitness += 0.1
                        all_fitness_values[car.fitness_id] = ge[i].fitness
                        if (adjusted_current_time - start_time) > 5.0:
                            if not car.has_won:
                                car.check_for_win(finish_line)
                                if car.has_won:
                                    winner_cars.append(car)
                                    winner_cars_finish_times.append(adjusted_current_time - start_time)
                                    last_gen_best_time = winner_cars_finish_times[0]
                                    if record_time == -1:
                                        record_time = winner_cars_finish_times[0]
                                    elif record_time > winner_cars_finish_times[0]:
                                        record_time = winner_cars_finish_times[0]
                                    index = winner_cars.index(car)
                                    if index == 0:
                                        point = 10
                                    elif index == 1:
                                        point = 5
                                    elif index == 2:
                                        point = 3
                                    else:
                                        point = 2
                                    ge[i].fitness += point

                        output = nets[i].activate(car.get_ray_distances())
                        if output[0] > 0.5:
                            car.rotate_all(4)
                        elif output[1] > 0.5:
                            car.rotate_all(-4)
                        elif output[2] > 0.5:
                            car.rotate_all(-8)
                        elif output[3] > 0.5:
                            car.rotate_all(8)
                        elif output[4] > 0.5:
                            pass
                        else:
                            pass
            else:
                print(time.time() - start_time)
                if testing_flag:
                    testing = True
                    testing_flag = False
                elif testing_flag is False and testing is True:
                    testing = False
                program = False
                break

            if camera_on:
                x_sum = 0
                y_sum = 0
                for car in cars:
                    x_sum += car.pos[0]
                    y_sum += car.pos[1]

                if len(cars) != 0:
                    x_avg = int(x_sum / len(cars))
                    y_avg = int(y_sum / len(cars))
                else:
                    x_avg = 0
                    y_avg = 0
                new_x = SW//2 - x_avg
                if new_x > 0:
                    new_x = 0
                if new_x < -420:
                    new_x = -420
                new_y = SH//2 - y_avg
                if new_y < -280:
                    new_y = -280
                if new_y > 0:
                    new_y = 0

                camera_pos[0] += (new_x - camera_pos[0])*0.1
                camera_pos[1] += (new_y - camera_pos[1])*0.1
            else:
                camera_pos = [0, 0]

            fitness_sum = 0
            for val in all_fitness_values:
                fitness_sum += val

            all_prev_fitness_avg[-1] = round(fitness_sum / len(all_fitness_values), 2)

            canvas2 = pg.transform.smoothscale(canvas, (1500, 1000) if camera_on else (1080, 720))
            window.blit(canvas2, camera_pos)
            draw_menu(window, ge, record_time, last_gen_best_time, generation_count, all_prev_fitness_avg)
        else:
            if pause_screen_drawn is False:
                pause_screen(window)
                pause_screen_drawn = True
        ui_manager.draw_ui(window)
        pg.display.update()


def run(config_path):
    config = neat.config.Config(neat.DefaultGenome, neat.DefaultReproduction,
                                neat.DefaultSpeciesSet, neat.DefaultStagnation,
                                config_path)

    p = neat.Population(config)
    p.add_reporter(neat.StdOutReporter(True))
    stats = neat.StatisticsReporter()
    p.add_reporter(stats)
    winner = p.run(main, 100)


if __name__ == "__main__":
    local_dir = os.path.dirname(__file__)
    config_path = os.path.join(local_dir, "assets/config_feedforward.txt")
    run(config_path)