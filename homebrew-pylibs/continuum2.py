"""Continuum 2.4.0

A 2D physics engine for Python, written on top of pygame.

Now with trigonometry-free vector math!"""

import pygame
from typing import Union, Sequence
import math
from utils import *

# Memory preallocation for window and its attributes
world = pygame.Surface((0, 0))
world_bg = (0, 0, 0)
render_offset_x = render_offset_y = 0
tick_delay = 10

# Object stack (contains all objects, removing one from the stack will result in it becoming no-clippable)
ObjectStack = []

# Elementary constants
G = 9.8
TIME_SCALE = 1  # Attunes time for Newtonian formula. At 1, t=0.01 s
AIR_DENSITY = 1.275
AERODYN_RESIS = 1.05


def build(w: int, h: int, title="Continuum Simulation", bg=(160, 160, 160)) -> None:
    global world
    global world_bg
    """Makes a Continuum world.
    w: The width of the world
    h: The height of the world
    title: The name of the world.
    bg: The background color of the world.
    """
    pygame.init()
    world = pygame.display.set_mode((w, h))
    world_bg = bg
    pygame.display.set_caption(title)


def screenTick() -> None:
    """Updates the window. Delays are built-in."""
    pygame.event.pump()
    pygame.display.flip()
    pygame.time.delay(tick_delay)
    world.fill(color=world_bg)

# Oooh, here comes the math!


class Vector:
    """A two-dimensional vector. Most commonly used to calculate forces and velocities.
    length: The scalar length of the vector. If less than zero, will raise ValueError.
    angle: Angle, in degrees. Any value is accepted. At ±180°, will be facing strictly to the left. At 0°, strictly to the right. At 90°, will be facing strictly down. At -90°, the opposite."""
    def __init__(self, length: float, angle: float) -> None:
        if length < 0:
            raise ValueError("Inappropriate length value. Must be more than zero.")
        self.length = length
        self.angle = angle
    
    def toProjections(self) -> list[float, float]:
        """Returns the projections on the X and Y axis."""
        return [self.length*math.cos(math.radians(self.angle)), self.length*math.sin(math.radians(self.angle))]
    
    @classmethod
    def fromProjections(class_, x: float, y: float):
        """A factory method that generates a Vector object from the given projections. Can be called directly from the class (Vector.fromProjections()).
        x: The projection along the X axis. Can be 0 or less.
        y: The projection along the Y axis. Can be 0 or less."""
        length = math.sqrt(x**2+y**2)
        angle = math.degrees(math.acos(safeDivision(x,length)))
        if y<0:
            angle*=-1
        return class_(length, angle)

    def listPoints(self, step=1, refCoords=[0,0]) -> list[list[float, float]]:
        """Returns a list of coordinates of the points that the vector passes.
        step: Optional. Specifies the threshold of the coordinates.
        refCoords: Optional. Specifies the reference coordinates of the listing."""
        res = []
        l = step
        while l <= self.length:
            res.append([Vector(l, self.angle).toProjections()[0]+refCoords[0], Vector(l, self.angle).toProjections()[1]+refCoords[1]])
            l += step
        return res
    
    def __add__(self, vec2):
        p1 = self.toProjections()
        p2 = vec2.toProjections()
        p = [0,0]
        for _ in range(2):
            p[_] = p1[_] + p2[_]
        return Vector.fromProjections(*p)

    def __sub__(self, vec2):
        p1 = self.toProjections()
        p2 = vec2.toProjections()
        p = [0,0]
        for _ in range(2):
            p[_] = p1[_] - p2[_]
        return Vector.fromProjections(*p)
    
    def __truediv__(self, scalar):
        p = self.toProjections()
        for _ in range(2):
            p[_] /= scalar
        return Vector.fromProjections(*p)

    def __mul__(self, scalar):
        p = self.toProjections()
        for _ in range(2):
            p[_] *= scalar
        return Vector.fromProjections(*p)


# Whew, no more math.


class Material:
    """Creates a custom material.
    frictionMult: Friction multiplier. 0 to make 'super slippery thing'.
    bounciness: Efficiency of the object's bounce (1=100%)"""

    def __init__(self, frictionMult: float, bounciness: float) -> None:
        self.frictMult = frictionMult
        self.bounciness = bounciness


class PhysObject:
    def __init__(self, x: float, y: float, surf: pygame.Surface, mass: float, material: Material) -> None:
        self.__ΣF = []
        # Position grid setup

        # 0;1 [] 2;1
        # []      []
        # 0;3 [] 2;3

        self.dim = [surf.get_width(), surf.get_height()]
        self.coords = [x, y, x+self.dim[0], y+self.dim[1]]

        self.mass = mass
        self.material = material

        self.surf = surf

        # Velocity
        self.vel = [0.0, 0.0]
        self.doNotPush = False  # Useful for games

        self.collides_with = {
            "down": None,
            "right": None,
            "left": None,
            "up": None,
        }

        # Adding to coll stack
        ObjectStack.append(self)

    def stdRender(self) -> None:
        "Renders the object using the default renderer."
        world.blit(
            self.surf, (self.coords[0]+render_offset_x, self.coords[1]+render_offset_y))

    def applyMotion(self):
        "Make the object move."
        self.collides_with = {
            "down": None,
            "right": None,
            "left": None,
            "up": None,
        }

        new_coors = [
            self.coords[0]+self.vel[0],
            self.coords[1]+self.vel[1],
            self.coords[2]+self.vel[0],
            self.coords[3]+self.vel[1]
        ]

        # RIGHTWARDS COLL WITH MULTIPLE OBJECTS <Done!>
        for obj in ObjectStack:

            # Skipping self and objects on left
            if obj == self or obj.coords[2] <= self.coords[0]:
                continue

            # Checking coll
            if new_coors[2] > obj.coords[0] and (self.coords[1] < obj.coords[3]) and (self.coords[3] > obj.coords[1]):
                new_coors[0] = obj.coords[0]-self.dim[0]
                new_coors[2] = new_coors[0]+self.dim[0]
                self.collides_with["right"] = obj
                # Applying friction, normal reaction and bounciness(tm)
                if self.vel[0] > 0:
                    if not obj.doNotPush:
                        N = Vector(0,0)
                        for F in self.__ΣF:
                            if 0<F.angle<180:
                                N += F
                        applyVectorForce(
                            obj, Vector.fromProjections(*(N.toProjections()))
                        )
                    # Normal reaction + bounciness
                    self.vel[0] -= self.vel[0]*(1+self.material.bounciness)

        # UPWARDS COLL WITH MULTIPLE OBJECTS <Done!>
        for obj in ObjectStack:

            # Skipping self and objects below
            if obj == self or obj.coords[1] >= self.coords[3]:
                continue

            # Checking coll
            if new_coors[1] < obj.coords[3] and (self.coords[0] < obj.coords[2]) and (self.coords[2] > obj.coords[0]):
                new_coors[1] = obj.coords[3]
                new_coors[3] = obj.coords[3]+self.dim[1]
                self.collides_with["up"] = obj
                # Applying friction, normal reaction and bounciness(tm)
                if self.vel[1] < 0:
                    if not obj.doNotPush:
                        ΣFy = Vector(0,0)
                        for F in self.__ΣF:
                            if 270<F.angle<=360 or 0<=F.angle<90:
                                ΣFy += F
                        applyVectorForce(obj, ΣFy)
                    # Normal reaction + bounciness
                    self.vel[1] -= self.vel[1]*(1+self.material.bounciness)

        # LEFTWARDS COLL WITH MULTIPLE OBJECTS <Done!>
        for obj in ObjectStack:

            # Skipping self and objects on right
            if obj == self or obj.coords[0] >= self.coords[2]:
                continue

            # Checking coll
            if new_coors[0] < obj.coords[2] and (self.coords[1] < obj.coords[3]) and (self.coords[3] > obj.coords[1]):
                new_coors[0] = obj.coords[2]
                new_coors[2] = new_coors[0]+self.dim[0]
                self.collides_with["left"] = obj
                # Applying friction, normal reaction and bounciness(tm)
                if self.vel[0] < 0:
                    if not obj.doNotPush:
                        N = Vector(0,0)
                        for F in self.__ΣF:
                            if 180<F.angle<360:
                                N += F
                        applyVectorForce(
                            obj, Vector.fromProjections(*(N.toProjections()))
                        )
                    # Normal reaction + bounciness
                    self.vel[0] -= self.vel[0]*(1+self.material.bounciness)

        # DOWNWARDS COLL WITH MULTIPLE OBJECTS <Done!>
        for obj in ObjectStack:

            # Skipping self and objects above
            if obj == self or obj.coords[3] <= self.coords[1]:
                continue

            # Checking coll
            if new_coors[3] > obj.coords[1] and (self.coords[0] < obj.coords[2]) and (self.coords[2] > obj.coords[0]):
                new_coors[1] = (obj.coords[1]-self.surf.get_height())
                new_coors[3] = obj.coords[1]
                self.collides_with["down"] = obj
                # Applying friction, normal reaction and bounciness(tm)
                if self.vel[1] > 0:
                    N = Vector(0,0)
                    for F in self.__ΣF:
                        if 90<F.angle<270:
                            N+=F
                    frictProj = self.material.frictMult*obj.material.frictMult * N.toProjections()[1]
                    vecAng = (Vector.fromProjections(self.vel[0], 0)*-1).angle
                    vec = Vector(frictProj, vecAng)
                    applyVectorForce(self, vec)
                    if not obj.doNotPush:
                        ΣFy = Vector(0,0)
                        for F in self.__ΣF:
                            if 180<F.angle<270:
                                ΣFy += F
                        applyVectorForce(obj, ΣFy)
                    # Normal reaction + bounciness
                    self.vel[1] -= self.vel[1]*(1+self.material.bounciness)

        self.coords = new_coors
        self.__ΣF = []


# Material presets
MAT_BASIC = Material(1, 0.06)
MAT_REBOUNCE = Material(1, 1)
MAT_SUPERSLIP = Material(0, 0)


def isWithinRange(d: float, u: float, n: float, uopen: bool, dopen: bool) -> bool:
    """Detect if n is within a certain range.
    If dopen and uopen is false, check within [d,u].
    If dopen is true, does not include d.
    If uopen is true, does not include u."""
    if uopen and dopen:
        if d < n and n < u:
            return True
        else:
            return False

    if uopen:
        pass

    if dopen:
        pass

    if d <= n and n <= u:
        return True
    else:
        return False


def fetchByAttr(attr: str, rule: str, val: object, amount=1) -> Union[PhysObject, list]:
    '''Fetches objects from the ObjectStack, by given
    attribute, rule and value.
    attr: Attribute to fetch. For example, ".coords[0]" fetches o.coords[0].
    rule: Rule to apply. For example, "==" checks if attr == val.
    val: Value to compare against.
    amount: Amount of objects to fetch.'''
    if not isinstance(amount, int):
        raise TypeError("amount must be a natural number")
    if amount < 1:
        raise ValueError("amount must be a natural number")
    res = []
    if amount == 1:
        del res
    for o in ObjectStack:
        if eval(f"o{attr} {rule} {val}"):
            if amount == 1:
                return o
            else:
                res.append(o)
    return res


def applyGravity(obj: PhysObject) -> None:
    obj.vel[1] += G*TIME_SCALE*0.01
    obj._PhysObject__ΣF.append(Vector(G*obj.mass, 180))

def applyVectorForce(obj: PhysObject, vec: Vector) -> None:
    projs = vec.toProjections()
    obj.vel[0] += projs[0]/obj.mass*TIME_SCALE*0.01
    obj.vel[1] += projs[1]/obj.mass*TIME_SCALE*0.01
    obj._PhysObject__ΣF.append(vec)


def applyAirResistance(obj: PhysObject) -> None:
    CORRECTION_COEF = 0.02786

    dims = [obj.dim[0]*CORRECTION_COEF, obj.dim[1]*CORRECTION_COEF]
    # aerodynamical resistance
    x = AERODYN_RESIS*((AIR_DENSITY*(obj.vel[0]**2))/2)*(dims[0]**2)
    y = AERODYN_RESIS*((AIR_DENSITY*(obj.vel[1]**2))/2)*(dims[1]**2)
    if obj.vel[0] > 0:
        x *= -1
    if obj.vel[1] > 0:
        y *= -1
    applyVectorForce(obj, Vector.fromProjections(x, y))
    obj._PhysObject__ΣF.append(Vector.fromProjections(x, y))


def toScalarForceProj(vel: float, obj: PhysObject):
    return vel/(0.01*TIME_SCALE)*obj.mass


class AttractionJoint:
    """Rope-like joint.
    obj1: Object no. 1
    obj2: Object no. 2
    maxDist: Maximum distance the objects can be apart from each other.
    hardness: Rope hardness, in N/m.
    weldpoint_offset1: How far is the welding point from the center of obj1.
    weldpoint_offset2: How far is the welding point from the center of obj2."""
    def __init__(self, obj1: PhysObject, obj2: PhysObject, maxDist: float, hardness: float, weldpoint1_offset=(0, 0), weldpoint2_offset=(0, 0)) -> None:
        self.obj1 = obj1
        self.obj2 = obj2
        self.maxDist = maxDist
        self.hardness = hardness
        self.wp1_off = weldpoint1_offset
        self.wp2_off = weldpoint2_offset
    
    def enforce(self) -> None:
        v = Vector.fromProjections(self.obj2.coords[0]-self.obj1.coords[0],self.obj2.coords[1]-self.obj1.coords[1])
        a1 = v.angle
        a2 = a1-180
        if v.length > self.maxDist:
            applyVectorForce(self.obj1, Vector((v.length-self.maxDist)*self.hardness, a1))
            applyVectorForce(self.obj2, Vector((v.length-self.maxDist)*self.hardness, a2))

    def stdRender(self, color: Sequence[int]) -> None:
        cent1 = [self.obj1.coords[0]+self.obj1.dim[0]/2+self.wp1_off[0],
                 self.obj1.coords[1]+self.obj1.dim[1]/2+self.wp1_off[1]]
        cent2 = [self.obj2.coords[0]+self.obj2.dim[0]/2+self.wp2_off[0],
                 self.obj2.coords[1]+self.obj2.dim[1]/2+self.wp2_off[1]]
        cent1[0] += render_offset_x
        cent2[0] += render_offset_x
        cent1[1] += render_offset_y
        cent2[1] += render_offset_y
        pygame.draw.line(world, color, cent1, cent2, 3)

class RepulsionJoint:
    """Spring-like joint, but only repulses.
    obj1: Object no. 1
    obj2: Object no. 2
    maxDist: Maximum distance the objects can be apart from each other.
    hardness: Rope hardness, in N/m.
    weldpoint_offset1: How far is the welding point from the center of obj1.
    weldpoint_offset2: How far is the welding point from the center of obj2."""
    def __init__(self, obj1: PhysObject, obj2: PhysObject, min: float, hardness: float, weldpoint1_offset=(0, 0), weldpoint2_offset=(0, 0)) -> None:
        self.obj1 = obj1
        self.obj2 = obj2
        self.minDist = min
        self.hardness = hardness
        self.wp1_off = weldpoint1_offset
        self.wp2_off = weldpoint2_offset
    
    def enforce(self) -> None:
        v = Vector.fromProjections(self.obj2.coords[0]-self.obj1.coords[0],self.obj2.coords[1]-self.obj1.coords[1])
        a1 = v.angle
        a2 = a1-180
        if v.length < self.minDist:
            applyVectorForce(self.obj1, Vector((self.minDist-v.length)*self.hardness, a1)*(-1))
            applyVectorForce(self.obj2, Vector((self.minDist-v.length)*self.hardness, a2)*(-1))

    def stdRender(self, color: Sequence[int]) -> None:
        cent1 = [self.obj1.coords[0]+self.obj1.dim[0]/2+self.wp1_off[0],
                 self.obj1.coords[1]+self.obj1.dim[1]/2+self.wp1_off[1]]
        cent2 = [self.obj2.coords[0]+self.obj2.dim[0]/2+self.wp2_off[0],
                 self.obj2.coords[1]+self.obj2.dim[1]/2+self.wp2_off[1]]
        cent1[0] += render_offset_x
        cent2[0] += render_offset_x
        cent1[1] += render_offset_y
        cent2[1] += render_offset_y
        pygame.draw.line(world, color, cent1, cent2, 1)
