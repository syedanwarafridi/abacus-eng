import numpy as np

class LineManager:
    def __init__(self):
        self.lines = {}
        self.next_id = 0
        self.counts = {i: 0 for i in range(7)}
        self.reference_width = 256 
        self.reference_height = 416
        self.track_history = {}
        self.routes = []  # Added
        self.route_counts = {}
        self.class_names = {
            0: "Passenger Car", 1: "Motorbike", 2: "Van",
            3: "Truck", 4: "Large Truck", 5: "Bus", 6: "Minibus"
        }
        

    def set_reference_size(self, width, height):
        self.reference_width = width
        self.reference_height = height

    def add_line(self, start, end):
        line_id = self.next_id
        self.lines[line_id] = {
            'id': line_id,
            'start': start,
            'end': end,
            'counted_objects': set()
        }
        self.next_id += 1
        return self.lines[line_id]
    
    def load_routes(self, routes):
        """Initialize counts for each class in each direction"""
        self.routes = routes
        self.route_counts = {
            (r["origin"], r["destination"]): {
                "direction": r["direction"],
                "counts": {cls: 0 for cls in range(7)}  # Counts per class
            } for r in routes
        }
        
    def reset(self):
        """Reset all state for new video"""
        self.lines.clear()
        self.next_id = 0
        self.route_counts.clear()
        self.track_history.clear()
        self.routes.clear()
        self.reference_width = 256
        self.reference_height = 416

    
    def check_line_crossing(self, detections, frame_shape):
        # Clear previous tracking data for new detections
        current_ids = {det['id'] for det in detections if det['id'] is not None}
        self.track_history = {k: v for k, v in self.track_history.items() if k in current_ids}

        # First pass: Update tracking history
        for det in detections:
            track_id = det['id']
            if track_id is None:
                continue
                
            if track_id not in self.track_history:
                self.track_history[track_id] = {
                    'crossed_lines': [],
                    'last_position': None,
                    'counted': False  # NEW: Flag to prevent double-counting
                }
            
            # Update position history
            self.track_history[track_id]['last_position'] = det['box']

        # Second pass: Check line crossings
        for line_id, line_data in self.lines.items():
            start = line_data['start']
            end = line_data['end']
            
            scale_x = frame_shape[1] / self.reference_width
            scale_y = frame_shape[0] / self.reference_height
            scaled_start = (start.x() * scale_x, start.y() * scale_y)
            scaled_end = (end.x() * scale_x, end.y() * scale_y)

            for det in detections:
                track_id = det['id']
                if track_id is None or self.track_history[track_id]['counted']:
                    continue

                if self._is_crossing_line(track_id, det['box'], scaled_start, scaled_end):
                    if line_id not in self.track_history[track_id]['crossed_lines']:
                        self.track_history[track_id]['crossed_lines'].append(line_id)

        # Third pass: Validate routes and update counts
        for track_id, history in self.track_history.items():
            if history['counted']:
                continue

            crossed = history['crossed_lines']
            vehicle_cls = next((d['cls'] for d in detections if d['id'] == track_id), None)

            if vehicle_cls is not None and len(crossed) >= 2:
                # Only count first valid route
                route_key = (crossed[0], crossed[1])
                
                if route_key in self.route_counts:
                    self.route_counts[route_key]["counts"][vehicle_cls] += 1
                    history['counted'] = True  # Mark as counted
                    print(f"Count updated for {self.route_counts[route_key]['direction']} "
                        f"({self.class_names[vehicle_cls]}): +1")
                    
    def _is_crossing_line(self, track_id, box, line_start, line_end):
        """Improved line crossing detection with direction checking"""
        x1, y1, x2, y2 = box
        center = ((x1 + x2) / 2, (y1 + y2) / 2)
        
        # Get previous position if exists
        prev_pos = self.track_history[track_id]['last_position']
        if prev_pos is None:
            return False
            
        (x1_line, y1_line), (x2_line, y2_line) = line_start, line_end
        
        # Check if center is near the line
        if (min(x1_line, x2_line) <= center[0] <= max(x1_line, x2_line)) and \
           (min(y1_line, y2_line) <= center[1] <= max(y1_line, y2_line)):
            numerator = abs((y2_line - y1_line)*center[0] - (x2_line - x1_line)*center[1] + x2_line*y1_line - y2_line*x1_line)
            denominator = ((y2_line - y1_line)**2 + (x2_line - x1_line)**2)**0.5
            return numerator/denominator < 5
        
        return False

    def set_reference_size(self, width, height):
        self.reference_width = width
        self.reference_height = height
        
    def reset(self):
        """Reset all counts and lines for new video"""
        self.lines.clear()
        self.next_id = 0
        self.counts = {i: 0 for i in range(7)}
        self.track_history.clear()
        self.reference_width = 256  # Reset to default
        self.reference_height = 416  # Reset to default