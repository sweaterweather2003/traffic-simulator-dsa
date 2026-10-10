from pathlib import Path
import textwrap

import pygame

from models.vehicle import Vehicle
from simulation.csv_logger import SimulationCsvLogger
from ml.online_learning import OnlineQueueLearner


WINDOW_WIDTH = 1080
WINDOW_HEIGHT = 720
PANEL_X = 790
MAP_WIDTH = 1900
MAP_HEIGHT = 1400
MAP_CENTER = (MAP_WIDTH // 2, MAP_HEIGHT // 2)
STEP_INTERVAL_MS = 450
LOG_PATH = Path(__file__).resolve().parents[1] / "data" / "simulation_log.csv"
CONTROLLERS = {
    pygame.K_1: ("fixed", "Fixed time"),
    pygame.K_2: ("longest_queue", "Longest queue"),
    pygame.K_3: ("max_pressure", "Max pressure"),
    pygame.K_4: ("fpac", "Forecast-informed"),
}


def run_viewer(simulator):
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("Interactive Traffic Signal Simulator")
    clock = pygame.time.Clock()
    title_font = pygame.font.SysFont("segoeui", 24, bold=True)
    font = pygame.font.SysFont("segoeui", 17)
    small_font = pygame.font.SysFont("segoeui", 14)

    running = True
    paused = True
    step_elapsed = 0
    movement_progress = 0.0
    camera_x = MAP_CENTER[0] - PANEL_X // 2
    camera_y = MAP_CENTER[1] - WINDOW_HEIGHT // 2
    camera_drag = None
    dragged_vehicle = None
    map_surface = pygame.Surface((MAP_WIDTH, MAP_HEIGHT))
    controller_name = "fpac"
    simulator.reset()
    simulator.controller_name = controller_name
    logger = SimulationCsvLogger(LOG_PATH)
    learner = OnlineQueueLearner()

    def seed_editor_vehicles():
        for direction, lane in simulator.intersection.lanes.items():
            for _ in range(2):
                vehicle = Vehicle(simulator.vehicle_id, direction, arrival_step=simulator.tick)
                if lane.enqueue(vehicle):
                    simulator.vehicles_created += 1
                simulator.vehicle_id += 1

    seed_editor_vehicles()

    def advance_simulation():
        lane_capacity = sum(lane.capacity for lane in simulator.intersection.lanes.values())
        before_features = state_features()
        simulator.step(controller_name)
        queue_total = sum(len(lane.queue) for lane in simulator.intersection.lanes.values())
        learner.observe(before_features, queue_total, lane_capacity)
        logger.log_step(simulator)

    def state_features():
        lane_capacities = [simulator.intersection.lanes[direction].capacity for direction in ("N", "E", "S", "W")]
        queue_features = [
            len(simulator.intersection.lanes[direction]) / max(1, capacity)
            for direction, capacity in zip(("N", "E", "S", "W"), lane_capacities)
        ]
        maximum_green = max(1, simulator.cfg.max_green_steps)
        return queue_features + [
            min(1.0, simulator.cfg.arrivals_per_step / 20.0),
            1.0 if simulator.phase == "NS" else 0.0,
            max(0, simulator.remaining) / maximum_green,
        ]

    def text(surface, value, position, color=(235, 240, 245), font_obj=font):
        surface.blit(font_obj.render(str(value), True, color), position)

    def vehicle_rect(direction, index, progress=0.0):
        center_x, center_y = MAP_CENTER
        spacing = 43
        direction_is_green = direction in simulator.opt.dirs(simulator.phase)
        advance = progress * spacing if direction_is_green else 0
        if direction == "N":
            rect = pygame.Rect(center_x - 65, center_y - 127 - index * spacing + advance, 30, 38)
        elif direction == "S":
            rect = pygame.Rect(center_x + 35, center_y + 127 + index * spacing - advance, 30, 38)
        elif direction == "W":
            rect = pygame.Rect(center_x - 128 - index * spacing + advance, center_y - 65, 38, 30)
        else:
            rect = pygame.Rect(center_x + 90 + index * spacing - advance, center_y + 35, 38, 30)
        return rect

    def draw_vehicle(surface, rect, emergency):
        color = (239, 91, 73) if emergency else (72, 166, 235)
        pygame.draw.rect(surface, color, rect, border_radius=6)
        pygame.draw.rect(surface, (220, 235, 248), rect, width=2, border_radius=6)
        pygame.draw.circle(surface, (245, 210, 92), (rect.centerx, rect.centery), 3)

    def draw_scene():
        center_x, center_y = MAP_CENTER
        map_surface.fill((48, 110, 76))
        pygame.draw.rect(map_surface, (57, 63, 70), (0, center_y - 80, MAP_WIDTH, 160))
        pygame.draw.rect(map_surface, (57, 63, 70), (center_x - 80, 0, 160, MAP_HEIGHT))

        road_mark = (190, 192, 180)
        for x in range(0, MAP_WIDTH, 48):
            pygame.draw.line(map_surface, road_mark, (x, center_y), (x + 24, center_y), 2)
        for y in range(0, MAP_HEIGHT, 48):
            pygame.draw.line(map_surface, road_mark, (center_x, y), (center_x, y + 24), 2)

        pygame.draw.line(map_surface, (245, 245, 230), (center_x - 80, center_y - 127), (center_x + 80, center_y - 127), 4)
        pygame.draw.line(map_surface, (245, 245, 230), (center_x - 80, center_y + 127), (center_x + 80, center_y + 127), 4)
        pygame.draw.line(map_surface, (245, 245, 230), (center_x - 128, center_y - 80), (center_x - 128, center_y + 80), 4)
        pygame.draw.line(map_surface, (245, 245, 230), (center_x + 128, center_y - 80), (center_x + 128, center_y + 80), 4)

        pygame.draw.rect(map_surface, (75, 80, 84), (center_x - 40, center_y - 40, 80, 80), border_radius=8)
        for direction, lane in simulator.intersection.lanes.items():
            for index, vehicle in enumerate(lane.queue):
                rect = vehicle_rect(direction, index, movement_progress if not paused else 0.0)
                if dragged_vehicle is None or vehicle is not dragged_vehicle["vehicle"]:
                    draw_vehicle(map_surface, rect, vehicle.emergency)

        if dragged_vehicle is not None:
            mouse_x, mouse_y = pygame.mouse.get_pos()
            rect = pygame.Rect(
                mouse_x + camera_x - dragged_vehicle["offset_x"],
                mouse_y + camera_y - dragged_vehicle["offset_y"],
                dragged_vehicle["width"],
                dragged_vehicle["height"],
            )
            draw_vehicle(map_surface, rect, dragged_vehicle["vehicle"].emergency)

        signal_color = (77, 211, 119) if simulator.phase == "NS" else (232, 74, 68)
        other_signal_color = (77, 211, 119) if simulator.phase == "EW" else (232, 74, 68)
        pygame.draw.circle(map_surface, signal_color, (center_x + 155, center_y - 100), 12)
        pygame.draw.circle(map_surface, other_signal_color, (center_x + 155, center_y + 100), 12)
        text(map_surface, "NS", (center_x + 172, center_y - 110), font_obj=small_font)
        text(map_surface, "EW", (center_x + 172, center_y + 90), font_obj=small_font)
        text(map_surface, "N", (center_x - 15, 18), font_obj=small_font)
        text(map_surface, "S", (center_x - 15, MAP_HEIGHT - 35), font_obj=small_font)
        text(map_surface, "W", (18, center_y - 8), font_obj=small_font)
        text(map_surface, "E", (MAP_WIDTH - 35, center_y - 8), font_obj=small_font)

        screen.fill((28, 39, 48))
        screen.blit(map_surface, (0, 0), pygame.Rect(camera_x, camera_y, PANEL_X, WINDOW_HEIGHT))
        pygame.draw.rect(screen, (20, 27, 35), (PANEL_X, 0, WINDOW_WIDTH - PANEL_X, WINDOW_HEIGHT))
        text(screen, "Traffic Lab", (PANEL_X + 24, 24), (255, 255, 255), title_font)
        text(screen, "Manual street view", (PANEL_X + 24, 58), (167, 184, 199), small_font)

        result = simulator.result()
        queue_ns = simulator.intersection.total_queue("NS")
        queue_ew = simulator.intersection.total_queue("EW")
        queues = [len(simulator.intersection.lanes[direction]) for direction in ("N", "E", "S", "W")]
        rows = [
            ("Controller", controller_name.replace("_", " ").title()),
            ("Signal", f"{simulator.phase} green, {simulator.remaining} ticks"),
            ("Simulation step", simulator.tick),
            ("Queues N / E / S / W", " / ".join(map(str, queues))),
            ("Vehicles served", simulator.throughput),
            ("Average wait", f"{result.average_wait:.1f} steps"),
            ("Maximum queue", result.max_queue),
            ("Mean arrivals / step", simulator.cfg.arrivals_per_step),
        ]
        y = 108
        for label, value in rows:
            text(screen, label, (PANEL_X + 24, y), (163, 181, 195), small_font)
            text(screen, value, (PANEL_X + 154, y), (245, 248, 250), small_font)
            y += 27

        pygame.draw.line(screen, (66, 79, 91), (PANEL_X + 24, y), (WINDOW_WIDTH - 24, y), 1)
        y += 12
        text(screen, "COACH", (PANEL_X + 24, y), (255, 208, 99), small_font)
        y += 19
        total_queue = queue_ns + queue_ew
        lane_capacity = sum(lane.capacity for lane in simulator.intersection.lanes.values())
        if paused:
            guidance = "Paused: drag a vehicle between approaches. Press N for one step or Space to run the controller."
        elif max(queues) >= simulator.cfg.lane_capacity * 0.75:
            busiest = ("N", "E", "S", "W")[queues.index(max(queues))]
            guidance = f"{busiest} queue is getting crowded. Expect slower discharge if arrivals keep exceeding green capacity."
        elif simulator.remaining <= 1:
            guidance = f"{simulator.phase} green is nearly over. Expect the next signal decision on the next step."
        else:
            guidance = f"{simulator.phase} is green for {simulator.remaining} more ticks. Up to two queued vehicles can pass per step."
        next_step = (
            f"Next step: about {simulator.cfg.arrivals_per_step} arrivals on average;"
            f" current total queue is {total_queue}."
        )
        for message in (guidance, next_step):
            for line in textwrap.wrap(message, width=37):
                text(screen, line, (PANEL_X + 24, y), (195, 207, 216), small_font)
                y += 16

        prediction = learner.predict(state_features(), lane_capacity)
        text(screen, "ONLINE LEARNING", (PANEL_X + 24, y + 3), (255, 208, 99), small_font)
        y += 22
        if learner.trained:
            error = learner.mean_absolute_error
            status = f"{learner.samples_seen} examples; MAE {error:.1f} vehicles" if error is not None else f"{learner.samples_seen} examples; scoring warm-up"
            forecast_line = f"Predicted next queue: {prediction:.1f} vehicles" if prediction is not None else "Waiting for the first forecast"
        else:
            status = f"Collecting examples: {learner.samples_seen}/{learner.WARMUP_SAMPLES} warm-up"
            forecast_line = "Prediction appears after warm-up"
        text(screen, status, (PANEL_X + 24, y), (195, 207, 216), small_font)
        text(screen, forecast_line, (PANEL_X + 24, y + 16), (195, 207, 216), small_font)
        y += 37
        text(screen, "Step data and model save automatically", (PANEL_X + 24, y), (163, 181, 195), small_font)
        y += 21
        pygame.draw.line(screen, (66, 79, 91), (PANEL_X + 24, y), (WINDOW_WIDTH - 24, y), 1)
        y += 9
        text(screen, "CONTROLS", (PANEL_X + 24, y), (255, 208, 99), small_font)
        y += 20
        controls = [
            "Space  Auto run / pause",
            "Drag  Move vehicles while paused",
            "N  Step | R  Reset",
            "1-4  Choose signal controller",
            "WASD / right-drag  Pan streets",
            "Up/Down  Change mean arrivals",
            "Esc  Quit",
        ]
        for control in controls:
            text(screen, control, (PANEL_X + 24, y), (195, 207, 216), small_font)
            y += 16
        status = "PAUSED" if paused else "RUNNING"
        status_color = (255, 208, 99) if paused else (104, 226, 147)
        text(screen, status, (PANEL_X + 24, WINDOW_HEIGHT - 42), status_color, font)
        pygame.display.flip()

    while running:
        elapsed = clock.tick(60)
        if not paused:
            step_elapsed += elapsed
            movement_progress = min(1.0, step_elapsed / STEP_INTERVAL_MS)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button in (2, 3) and event.pos[0] < PANEL_X:
                    camera_drag = event.pos
                elif event.button == 1 and paused and event.pos[0] < PANEL_X:
                    world_x = event.pos[0] + camera_x
                    world_y = event.pos[1] + camera_y
                    for direction, lane in simulator.intersection.lanes.items():
                        for index, vehicle in enumerate(lane.queue):
                            rect = vehicle_rect(direction, index)
                            if rect.collidepoint(world_x, world_y):
                                del lane.queue[index]
                                dragged_vehicle = {
                                    "vehicle": vehicle,
                                    "lane": lane,
                                    "index": index,
                                    "offset_x": world_x - rect.x,
                                    "offset_y": world_y - rect.y,
                                    "width": rect.width,
                                    "height": rect.height,
                                }
                                break
                        if dragged_vehicle is not None:
                            break
            elif event.type == pygame.MOUSEMOTION:
                if camera_drag is not None:
                    camera_x -= event.pos[0] - camera_drag[0]
                    camera_y -= event.pos[1] - camera_drag[1]
                    camera_x = max(0, min(MAP_WIDTH - PANEL_X, camera_x))
                    camera_y = max(0, min(MAP_HEIGHT - WINDOW_HEIGHT, camera_y))
                    camera_drag = event.pos
            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button in (2, 3):
                    camera_drag = None
                elif event.button == 1 and dragged_vehicle is not None:
                    mouse_x, mouse_y = pygame.mouse.get_pos()
                    drop_x = mouse_x + camera_x - dragged_vehicle["offset_x"] + dragged_vehicle["width"] // 2
                    drop_y = mouse_y + camera_y - dragged_vehicle["offset_y"] + dragged_vehicle["height"] // 2
                    center_x, center_y = MAP_CENTER
                    candidates = []
                    if drop_y < center_y - 80:
                        candidates.append(("N", abs(drop_x - (center_x - 50))))
                    if drop_y > center_y + 80:
                        candidates.append(("S", abs(drop_x - (center_x + 50))))
                    if drop_x < center_x - 80:
                        candidates.append(("W", abs(drop_y - (center_y - 50))))
                    if drop_x > center_x + 80:
                        candidates.append(("E", abs(drop_y - (center_y + 50))))
                    if candidates:
                        direction = min(candidates, key=lambda candidate: candidate[1])[0]
                        lane = simulator.intersection.lanes[direction]
                        if len(lane.queue) < lane.capacity:
                            if direction == "N":
                                index = round((center_y - 127 - drop_y) / 43)
                            elif direction == "S":
                                index = round((drop_y - center_y - 127) / 43)
                            elif direction == "W":
                                index = round((center_x - 128 - drop_x) / 43)
                            else:
                                index = round((drop_x - center_x - 90) / 43)
                            lane.queue.insert(max(0, min(index, len(lane.queue))), dragged_vehicle["vehicle"])
                        else:
                            dragged_vehicle["lane"].queue.insert(
                                min(dragged_vehicle["index"], len(dragged_vehicle["lane"].queue)),
                                dragged_vehicle["vehicle"],
                            )
                    else:
                        dragged_vehicle["lane"].queue.insert(
                            min(dragged_vehicle["index"], len(dragged_vehicle["lane"].queue)),
                            dragged_vehicle["vehicle"],
                        )
                    dragged_vehicle = None
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_SPACE:
                    paused = not paused
                elif event.key == pygame.K_n and paused:
                    advance_simulation()
                    step_elapsed = 0
                    movement_progress = 0.0
                elif event.key == pygame.K_r:
                    simulator.reset()
                    simulator.controller_name = controller_name
                    seed_editor_vehicles()
                    logger.start_new_run()
                    step_elapsed = 0
                    movement_progress = 0.0
                elif event.key in CONTROLLERS:
                    controller_name = CONTROLLERS[event.key][0]
                    simulator.controller_name = controller_name
                elif event.key == pygame.K_UP:
                    simulator.cfg.arrivals_per_step = min(20, simulator.cfg.arrivals_per_step + 1)
                elif event.key == pygame.K_DOWN:
                    simulator.cfg.arrivals_per_step = max(0, simulator.cfg.arrivals_per_step - 1)
                elif event.key in (pygame.K_a, pygame.K_LEFT):
                    camera_x = max(0, camera_x - 60)
                elif event.key in (pygame.K_d, pygame.K_RIGHT):
                    camera_x = min(MAP_WIDTH - PANEL_X, camera_x + 60)
                elif event.key == pygame.K_w:
                    camera_y = max(0, camera_y - 60)
                elif event.key == pygame.K_s:
                    camera_y = min(MAP_HEIGHT - WINDOW_HEIGHT, camera_y + 60)

        if not paused and step_elapsed >= STEP_INTERVAL_MS:
            advance_simulation()
            step_elapsed %= STEP_INTERVAL_MS
            movement_progress = 0.0
        draw_scene()

    logger.close()
    learner.save()
    pygame.quit()
