import math

class Disc:
    def __init__(self, center_x, center_y, radius):
        self.center_x = center_x
        self.center_y = center_y
        self.radius = radius

def angle_between_lines(line1, line2):
    """
    Calculate the positive angle swept clockwise between two lines.
    
    :param line1: First line defined by its angle
    :param line2: Second line defined by its angle
    :return: Positive angle between the lines
    """
    angle = line2[0] - line1[0]
    return angle if angle >= 0 else angle + 2 * math.pi

def is_line_support(disc1, disc2):
    """
    Determine if there's a supporting line between two discs.
    
    :param disc1: First disc
    :param disc2: Second disc
    :return: Supporting line or None
    """
    # Calculate center distance
    dx = disc2.center_x - disc1.center_x
    dy = disc2.center_y - disc1.center_y
    center_dist = math.sqrt(dx * dx + dy * dy)
    
    # Check if discs have a supporting line
    if center_dist > disc1.radius + disc2.radius:
        # Line angle from disc1 to disc2
        line_angle = math.atan2(dy, dx)
        return (line_angle, center_dist)
    
    return None

def compute_convex_hull(discs):
    """
    Compute the convex hull of a set of discs using a divide and conquer approach.
    
    :param discs: List of discs
    :return: List representing the convex hull of discs
    """
    def merge_hulls(hull1, hull2):
        """
        Merge two convex hulls of discs.
        
        :param hull1: First hull
        :param hull2: Second hull
        :return: Merged hull
        """
        if not hull1:
            return hull2
        if not hull2:
            return hull1
        
        # Initial supporting lines for both hulls
        current_angle = 0
        merged_hull = []
        
        # Use two pointers to track positions in each hull
        i, j = 0, 0
        
        while i < len(hull1) or j < len(hull2):
            # Find next supporting line
            best_disc = None
            best_angle = float('inf')
            
            # Check disc from first hull
            if i < len(hull1):
                support = is_line_support(hull2[j % len(hull2)], hull1[i])
                if support:
                    angle = angle_between_lines((current_angle, 0), support)
                    if angle < best_angle:
                        best_disc = hull1[i]
                        best_angle = angle
            
            # Check disc from second hull
            if j < len(hull2):
                support = is_line_support(hull1[i % len(hull1)], hull2[j])
                if support:
                    angle = angle_between_lines((current_angle, 0), support)
                    if angle < best_angle:
                        best_disc = hull2[j]
                        best_angle = angle
            
            # Add best disc to merged hull
            if best_disc:
                merged_hull.append(best_disc)
                current_angle += best_angle
                
                # Advance pointer for the hull of the best disc
                if best_disc in hull1:
                    i += 1
                else:
                    j += 1
            
            # If no more discs, break
            if i >= len(hull1) and j >= len(hull2):
                break
        
        return merged_hull
    
    def recursive_hull(subset):
        """
        Recursively compute convex hull for a subset of discs.
        
        :param subset: Subset of discs
        :return: Convex hull of the subset
        """
        # Base cases
        if len(subset) <= 1:
            return subset
        if len(subset) == 2:
            support = is_line_support(subset[0], subset[1])
            return subset if support else []
        
        # Divide step
        mid = len(subset) // 2
        left_hull = recursive_hull(subset[:mid])
        right_hull = recursive_hull(subset[mid:])
        
        # Merge step
        return merge_hulls(left_hull, right_hull)
    
    # Sort discs if needed to ensure consistent results
    sorted_discs = sorted(discs, key=lambda d: (d.center_x, d.center_y))
    return recursive_hull(sorted_discs)

# Example usage
def main():
    # Example set of discs
    discs = [
        Disc(0, 0, 1),
        Disc(2, 2, 1.5),
        Disc(4, 1, 1),
        Disc(1, 3, 0.5),
        Disc(3, 4, 0.75)
    ]
    
    hull = compute_convex_hull(discs)
    print("Convex Hull Discs:")
    for disc in hull:
        print(f"Disc at ({disc.center_x}, {disc.center_y}) with radius {disc.radius}")

if __name__ == "__main__":
    main()