from pathlib import Path
import textwrap

import pygame

from ml.online_learning import OnlineQueueLearner
from simulation.network_csv_logger import NetworkCsvLogger
from simulation.route_advisor import recommend_routes, steps_to_minutes


WINDOW_WIDTH = 1180
WINDOW_HEIGHT = 760
PANEL_X = 850
STEP_INTERVAL_MS = 1000
NODE_POSITIONS = {
    "A": (260, 210),
    "B": (600, 210),
    "C": (260, 510),
    "D": (600, 510),
}
LOG_PATH = Path(__file__).resolve().parents[1] / "data" / "network_simulation_log_v2.csv"
CONTROLLERS = {
    pygame.K_1: "fixed",
    pygame.K_2: "longest_queue",
    pygame.K_3: "max_pressure",
    pygame.K_4: "forecast",
    pygame.K_5: "spillback",
}


def run_network_viewer(simulator, controller="spillback", policy=None):
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("Multi-Intersection Traffic Network")
    clock = pygame.time.Clock()
    title_font = pygame.font.SysFont("segoeui", 24, bold=True)
    font = pygame.font.SysFont("segoeui", 16)
    small_font = pygame.font.SysFont("segoeui", 13)
    logger = NetworkCsvLogger(LOG_PATH)
    learner = OnlineQueueLearner(
        Path(__file__).resolve().parents[1]
        / "models_saved"
        / "interactive_network_queue_sgd.joblib"
    )
    simulator.reset()

    running = True
    paused = True
    manual_mode = True
    accident_mode = False
    elapsed_step = 0
    progress = 0.0
    route_origin = simulator.cfg.nodes[0]
    route_destination = simulator.cfg.nodes[-1]
    if route_origin == route_destination:
        route_destination = simulator.cfg.nodes[1]

    def label(value, position, color=(230, 237, 243), font_obj=font):
        screen.blit(font_obj.render(str(value), True, color), position)

    def advance():
        before_features = network_features()
        if controller == "ppo":
            if policy is None:
                raise ValueError("The PPO network viewer requires a trained policy.")
            action, _ = policy.predict(simulator.get_observation(), deterministic=True)
            simulator.step("ppo", actions=action, spawn_traffic=not manual_mode)
        else:
            simulator.step(controller, spawn_traffic=not manual_mode)
        queue_capacity = sum(lane.capacity for lane in simulator.queues.values())
        learner.observe(before_features, simulator.result(controller).total_queue, queue_capacity)
        logger.log_step(simulator, controller)

    def network_features():
        queue_capacity = sum(lane.capacity for lane in simulator.queues.values())
        queue_features = [
            len(lane) / max(1, lane.capacity)
            for lane in simulator.queues.values()
        ]
        forecast = sum(simulator.current_forecast.values())
        forecast_scale = max(1.0, simulator.cfg.arrivals_per_step * len(simulator.cfg.nodes))
        return queue_features + [
            min(1.0, simulator.cfg.arrivals_per_step / 20.0),
            min(2.0, forecast / forecast_scale),
            sum(phase == "NS" for phase in simulator.signals.values()) / len(simulator.cfg.nodes),
            sum(simulator.remaining_green.values()) / (
                len(simulator.cfg.nodes) * max(1, simulator.cfg.max_green_steps)
            ),
            len(simulator.incidents) / max(1, len(simulator.cfg.edges) * 2),
        ]

    def draw_car(position, color, horizontal):
        px, py = position
        width, height = (24, 15) if horizontal else (15, 24)
        body = pygame.Rect(px - width // 2, py - height // 2, width, height)
        pygame.draw.rect(screen, color, body, border_radius=5)
        pygame.draw.rect(screen, (229, 239, 242), body, width=1, border_radius=5)
        if horizontal:
            window = pygame.Rect(px - 5, py - 4, 10, 8)
        else:
            window = pygame.Rect(px - 4, py - 5, 8, 10)
        pygame.draw.rect(screen, (183, 221, 229), window, border_radius=2)

    def draw_roads(best_route):
        screen.fill((31, 45, 49))
        pygame.draw.rect(screen, (49, 104, 75), (0, 0, PANEL_X, WINDOW_HEIGHT))
        for source, destination in simulator.cfg.edges:
            start, end = NODE_POSITIONS[source], NODE_POSITIONS[destination]
            pygame.draw.line(screen, (67, 72, 77), start, end, 78)
            pygame.draw.line(screen, (194, 194, 177), start, end, 2)
            middle = ((start[0] + end[0]) // 2, (start[1] + end[1]) // 2)
            pygame.draw.circle(screen, (222, 190, 91), middle, 5)

        if best_route:
            for source, destination in zip(best_route, best_route[1:]):
                pygame.draw.line(
                    screen,
                    (81, 202, 146),
                    NODE_POSITIONS[source],
                    NODE_POSITIONS[destination],
                    7,
                )

        for source, destination in simulator.cfg.edges:
            if simulator.incidents.get((source, destination), 0) <= 0:
                continue
            start = NODE_POSITIONS[source]
            end = NODE_POSITIONS[destination]
            middle = ((start[0] + end[0]) // 2, (start[1] + end[1]) // 2)
            pygame.draw.line(screen, (189, 62, 50), start, end, 16)
            pygame.draw.line(screen, (248, 188, 79), start, end, 3)
            draw_car((middle[0] - 12, middle[1]), (239, 91, 73), start[0] != end[0])
            draw_car((middle[0] + 12, middle[1]), (242, 132, 76), start[0] != end[0])
            label("!", (middle[0] - 4, middle[1] - 34), (255, 223, 106), title_font)
            label(f"CRASH {simulator.incidents[(source, destination)]}s", (middle[0] - 36, middle[1] + 20), (255, 223, 106), small_font)

        for node in simulator.cfg.nodes:
            x, y = NODE_POSITIONS[node]
            pygame.draw.circle(screen, (79, 83, 85), (x, y), 52)
            pygame.draw.circle(screen, (185, 190, 179), (x, y), 52, 2)
            phase = simulator.signals[node]
            if phase == "CLEAR":
                north_south, east_west = (243, 186, 66), (243, 186, 66)
            else:
                north_south = (69, 215, 119) if phase == "NS" else (227, 73, 68)
                east_west = (69, 215, 119) if phase == "EW" else (227, 73, 68)
            pygame.draw.circle(screen, north_south, (x - 12, y - 12), 7)
            pygame.draw.circle(screen, east_west, (x + 12, y - 12), 7)
            label(node, (x - 5, y + 8), (255, 255, 255), font)
            label(
                f"{phase}  {simulator.clearance_remaining[node] or simulator.remaining_green[node]}",
                (x - 35, y + 58),
                (240, 240, 225),
                small_font,
            )

            for key, lane in simulator.queues.items():
                if key[1] != node:
                    continue
                direction = simulator.queue_directions[key]
                if key[0].startswith("EXT-"):
                    source_x, source_y = x, y
                    if direction == "N":
                        source_y -= 122
                    elif direction == "S":
                        source_y += 122
                    elif direction == "W":
                        source_x -= 122
                    else:
                        source_x += 122
                else:
                    source_x, source_y = NODE_POSITIONS[key[0]]
                travel_steps = simulator.cfg.approach_travel_steps if key[0].startswith("EXT-") else simulator.cfg.edge_travel_steps
                for index, vehicle in enumerate(list(lane.queue)[:10]):
                    ratio = min(1.0, (simulator.tick - vehicle.edge_entry_step + progress) / travel_steps)
                    ratio = max(0.02, ratio - index * 0.055)
                    px = int(source_x + (x - source_x) * ratio)
                    py = int(source_y + (y - source_y) * ratio)
                    color = (239, 91, 73) if vehicle.emergency else (72, 166, 235)
                    horizontal = source_x != x
                    draw_car((px, py), color, horizontal)

    def draw_bubble(route_options):
        bubble = pygame.Rect(20, 20, 590, 96)
        pygame.draw.rect(screen, (24, 38, 39), bubble.move(0, 4), border_radius=14)
        pygame.draw.rect(screen, (250, 247, 221), bubble, border_radius=14)
        pygame.draw.rect(screen, (40, 70, 66), bubble, width=2, border_radius=14)
        pygame.draw.polygon(screen, (250, 247, 221), [(54, 116), (74, 116), (59, 132)])
        pygame.draw.circle(screen, (112, 194, 157), (48, 53), 17)
        pygame.draw.circle(screen, (36, 73, 66), (42, 50), 2)
        pygame.draw.circle(screen, (36, 73, 66), (54, 50), 2)
        pygame.draw.arc(screen, (36, 73, 66), (41, 51, 14, 12), 3.4, 5.9, 2)

        if accident_mode:
            message = "Crash mode is on. Click a road to block it for 120 seconds; cars will queue behind the closure."
        elif manual_mode:
            message = f"Manual traffic: press V to release one car from {route_origin} to {route_destination}. Cars obey signals and wait at red."
        elif simulator.last_incident_blocked:
            message = f"Crash blockage! {simulator.last_incident_blocked} car(s) could not pass this step. Expect a queue behind the wreck."
        elif not route_options:
            message = f"Choose two different intersections for a trip from {route_origin} to {route_destination}."
        elif len(route_options) == 1:
            path, steps = route_options[0]
            message = f"Only one open path: {' - '.join(path)}. I estimate {steps_to_minutes(steps):.1f} min right now."
        else:
            best_path, best_steps = route_options[0]
            slow_path, slow_steps = route_options[-1]
            savings = steps_to_minutes(slow_steps - best_steps)
            if savings >= 0.1:
                message = (
                    f"Try {' - '.join(best_path)} to dodge the queue. About "
                    f"{steps_to_minutes(best_steps):.1f} min, vs "
                    f"{steps_to_minutes(slow_steps):.1f} min on {' - '.join(slow_path)}."
                )
            else:
                message = (
                    f"No clear shortcut right now. {' - '.join(best_path)} is about "
                    f"{steps_to_minutes(best_steps):.1f} min; I’ll keep watching!"
                )

        label("ROAD BUDDY", (77, 34), (43, 91, 78), small_font)
        for line_index, line in enumerate(textwrap.wrap(message, width=59)[:3]):
            label(line, (77, 55 + line_index * 17), (36, 56, 53), small_font)

    def draw_panel(route_options):
        pygame.draw.rect(screen, (20, 28, 36), (PANEL_X, 0, WINDOW_WIDTH - PANEL_X, WINDOW_HEIGHT))
        label("Network Traffic Lab", (PANEL_X + 24, 22), (255, 255, 255), title_font)
        result = simulator.result(controller)
        rows = [
            ("Controller", controller.replace("_", " ").title()),
            ("Step", simulator.tick),
            ("Vehicles served", result.throughput),
            ("Vehicles waiting", result.total_queue),
            ("Completed trips", result.completed_trips),
            ("Average wait", f"{result.average_wait:.1f} s"),
            ("Average travel", f"{result.average_travel_time:.1f} s"),
            ("Accident blocked", result.incident_blocked),
            ("Background arrivals", "OFF" if manual_mode else "ON"),
        ]
        queue_capacity = sum(lane.capacity for lane in simulator.queues.values())
        predicted_queue = learner.predict(network_features(), queue_capacity)
        queue_mae = learner.mean_absolute_error
        rows.extend([
            ("PEMS-guided next queue", f"{predicted_queue:.1f}" if predicted_queue is not None else "warming up"),
            ("Game prequential MAE", f"{queue_mae:.1f} vehicles" if queue_mae is not None else "collecting samples"),
        ])
        y = 62
        for name, value in rows:
            label(name, (PANEL_X + 24, y), (166, 184, 198), small_font)
            label(value, (PANEL_X + 186, y), (230, 237, 243), small_font)
            y += 29
        pygame.draw.line(screen, (67, 80, 92), (PANEL_X + 24, y), (WINDOW_WIDTH - 24, y), 1)
        y += 10
        label("TRIP ESTIMATES (1 SEC / SIM STEP)", (PANEL_X + 24, y), (255, 208, 99), small_font)
        y += 21
        label(f"{route_origin} to {route_destination}  |  click start, Shift-click end", (PANEL_X + 24, y), (195, 207, 216), small_font)
        y += 22
        if route_options:
            for index, (path, steps) in enumerate(route_options[:3]):
                route_color = (104, 226, 147) if index == 0 else (195, 207, 216)
                label(
                    f"{' - '.join(path)}   {steps_to_minutes(steps):.1f} min",
                    (PANEL_X + 24, y),
                    route_color,
                    small_font,
                )
                y += 19
        else:
            label("Select two different nodes.", (PANEL_X + 24, y), (195, 207, 216), small_font)
            y += 19
        y += 5
        pygame.draw.line(screen, (67, 80, 92), (PANEL_X + 24, y), (WINDOW_WIDTH - 24, y), 1)
        y += 9
        label("CONTROLS", (PANEL_X + 24, y), (255, 208, 99), small_font)
        y += 19
        controls = [
            "Click node: trip start | Shift-click: trip end",
            "V  Release one car on selected route",
            "I  Accident mode | click road to cause crash",
            "C  Clear all accidents | M  Toggle traffic",
            "Space  Run / pause | N  Advance one second",
            "1-5  Signals | 6  PPO | R  Reset | Esc  Quit",
        ]
        for control in controls:
            label(control, (PANEL_X + 24, y), (195, 207, 216), small_font)
            y += 21
        label("PEMS RF conditions the queue forecast; each game step is scored before model update.",
              (PANEL_X + 24, y + 3), (163, 181, 195), small_font)
        label("PAUSED" if paused else "RUNNING", (PANEL_X + 24, WINDOW_HEIGHT - 34),
              (255, 208, 99) if paused else (104, 226, 147))

    def draw():
        route_options = recommend_routes(simulator, route_origin, route_destination)
        best_route = route_options[0][0] if route_options else ()
        draw_roads(best_route)
        draw_bubble(route_options)
        draw_panel(route_options)
        pygame.display.flip()

    try:
        while running:
            elapsed_step += clock.tick(60)
            progress = min(1.0, elapsed_step / STEP_INTERVAL_MS)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if accident_mode and event.pos[0] < PANEL_X:
                        clicked_edge = min(
                            simulator.cfg.edges,
                            key=lambda edge: pygame.Vector2(event.pos).distance_to(
                                ((NODE_POSITIONS[edge[0]][0] + NODE_POSITIONS[edge[1]][0]) / 2,
                                 (NODE_POSITIONS[edge[0]][1] + NODE_POSITIONS[edge[1]][1]) / 2)
                            ),
                        )
                        midpoint = (
                            (NODE_POSITIONS[clicked_edge[0]][0] + NODE_POSITIONS[clicked_edge[1]][0]) / 2,
                            (NODE_POSITIONS[clicked_edge[0]][1] + NODE_POSITIONS[clicked_edge[1]][1]) / 2,
                        )
                        if pygame.Vector2(event.pos).distance_to(midpoint) <= 50:
                            simulator.set_incident(clicked_edge, duration_steps=120)
                        continue
                    clicked_node = min(
                        simulator.cfg.nodes,
                        key=lambda node: pygame.Vector2(event.pos).distance_to(NODE_POSITIONS[node]),
                    )
                    if pygame.Vector2(event.pos).distance_to(NODE_POSITIONS[clicked_node]) <= 52:
                        if pygame.key.get_mods() & pygame.KMOD_SHIFT:
                            if clicked_node != route_origin:
                                route_destination = clicked_node
                        else:
                            route_origin = clicked_node
                            if route_origin == route_destination:
                                route_destination = next(
                                    node for node in simulator.cfg.nodes if node != route_origin
                                )
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_SPACE:
                        paused = not paused
                    elif event.key == pygame.K_n and paused:
                        advance()
                        elapsed_step = 0
                    elif event.key == pygame.K_r:
                        simulator.reset()
                        logger.start_new_run()
                        elapsed_step = 0
                    elif event.key == pygame.K_v:
                        simulator.add_vehicle(route_origin, route_destination)
                    elif event.key == pygame.K_i:
                        accident_mode = not accident_mode
                    elif event.key == pygame.K_c:
                        simulator.incidents.clear()
                    elif event.key == pygame.K_m:
                        manual_mode = not manual_mode
                    elif event.key in CONTROLLERS:
                        controller = CONTROLLERS[event.key]
                    elif event.key == pygame.K_6 and policy is not None:
                        controller = "ppo"
                    elif event.key == pygame.K_UP:
                        simulator.cfg.arrivals_per_step = min(20, simulator.cfg.arrivals_per_step + 1)
                    elif event.key == pygame.K_DOWN:
                        simulator.cfg.arrivals_per_step = max(0, simulator.cfg.arrivals_per_step - 1)

            if not paused and elapsed_step >= STEP_INTERVAL_MS:
                advance()
                elapsed_step %= STEP_INTERVAL_MS
            draw()
    finally:
        logger.close()
        learner.save()
        pygame.quit()
