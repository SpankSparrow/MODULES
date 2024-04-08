import warnings
from typing import Union, Tuple, Dict, Optional, Any

import pygame
from pygame_gui.core.utility import translate

from pygame_gui.core import ObjectID
from pygame_gui.core.interfaces import IContainerLikeInterface, IUIManagerInterface
from pygame_gui.core.interfaces import IUITextOwnerInterface
from pygame_gui.core.drawable_shapes import RectDrawableShape
from pygame_gui._constants import UITextEffectType, TEXT_EFFECT_TYPING_APPEAR, TEXT_EFFECT_FADE_IN, TEXT_EFFECT_FADE_OUT
from pygame_gui.core.text.text_effects import TypingAppearEffect, FadeInEffect, FadeOutEffect
from pygame_gui.core.text import TextLineChunkFTFont

from pygame.sprite import Sprite  # Import Sprite

class UIElement(Sprite, IUITextOwnerInterface):
    """
    Base class for GUI elements.
    """

    def __init__(self, relative_rect: pygame.Rect,
                manager: Optional[IUIManagerInterface] = None,
                container: Optional[IContainerLikeInterface] = None,
                parent_element: Optional['UIElement'] = None,
                object_id: Optional[Union[ObjectID, str]] = None,
                anchors: Optional[Dict[str, Union[str, 'UIElement']]] = None,
                visible: int = 1,
                starting_height: int = 1,
                layer_thickness: int = 1,
                *,
                text: Optional[str] = None,
                text_colour: Optional[pygame.Color] = None,
                bg_colour: Optional[pygame.Color] = None,
                manager_object_id: Optional[Union[ObjectID, str]] = None,
                tool_tip_text: Optional[str] = None):

        # Initialize the Sprite class
        super().__init__()  

        self.relative_rect = relative_rect
        self.manager = manager
        self.container = container
        self.parent_element = parent_element
        self.object_id = object_id
        self.anchors = anchors
        self.visible = visible
        self.starting_height = starting_height
        self.layer_thickness = layer_thickness
        self.text = text
        self.text_colour = text_colour
        self.bg_colour = bg_colour
        self.manager_object_id = manager_object_id
        self.tool_tip_text = tool_tip_text

        self.drawable_shape = RectDrawableShape(self.relative_rect, self.manager.ui_theme)

        self._create_valid_ids(container=container,
                               parent_element=parent_element,
                               object_id=object_id,
                               element_id=None)

        if self.manager is not None and self.manager_object_id is not None:
            self.manager.register_group(self.manager_object_id, self)

        self.hovered = False

        self.tooltip = None
        self.is_enabled = True
        self.ui_group = None

        self._tooltip_rendered_text = None
        self._last_colour_and_image = None

        self.aligned_text_render = None
        self.tool_tip_text_render = None

        self.ui_manager = None

        self.shadow_text = None
        self.shadow_text_render = None

        self.dynamic_width = self.relative_rect.width == -1
        self.dynamic_height = self.relative_rect.height == -1

        if self.dynamic_width:
            self.dynamic_width = False
            self.relative_rect.width = 0

        if self.dynamic_height:
            self.dynamic_height = False
            self.relative_rect.height = 0

        self.drawable_shape = RectDrawableShape(self.relative_rect, self.manager.ui_theme)

        self.border_colour = None
        self.border_width = 0

        self.shape_type = 'rect'

        self.image = None
        self.tool_tip_text_surfaces = []
        self.bg_colour = pygame.Color(0, 0, 0, 0)
        self.is_focused = False
        self.horizontal_scroll_bar = None
        self.vertical_scroll_bar = None
        self.image_to_draw = None

        self._update_current_size()

        self.shadow = False
        self.shadow_colour = pygame.Color('#000000')
        self.shadow_offset = (1, 1)
        self.shadow_width = 1

        self.check_hover_time = 0.5
        self.hover_time = 0.0



    def change_layer(self, new_layer):
        self._layer = new_layer
        self.ui_group.change_layer(self, new_layer)


    def _get_clamped_to_minimum_dimensions(self, dimensions, clamp_to_container=False):
        if self.ui_container is not None and clamp_to_container:
            dimensions = (min(self.ui_container.rect.width,
                              max(self.minimum_dimensions[0],
                                  int(dimensions[0]))),
                          min(self.ui_container.rect.height,
                              max(self.minimum_dimensions[1],
                                  int(dimensions[1]))))
        else:
            dimensions = (max(self.minimum_dimensions[0], int(dimensions[0])),
                          max(self.minimum_dimensions[1], int(dimensions[1])))
        return dimensions

    def _on_contents_changed(self):
        if self.dynamic_width or self.dynamic_height:
            self._calc_dynamic_size()

    def _calc_dynamic_size(self):
        pass

    @staticmethod
    def _validate_horizontal_anchors(anchors: Dict[str, Union[str, 'UIElement']]):
        # first make a dictionary of just the horizontal anchors
        horizontal_anchors = {}

        if 'left' in anchors:
            horizontal_anchors.update({'left': anchors['left']})
        if 'right' in anchors:
            horizontal_anchors.update({'right': anchors['right']})
        if 'centerx' in anchors:
            horizontal_anchors.update({'centerx': anchors['centerx']})

        valid_anchor_set = [{'left': 'left', 'right': 'left'},
                            {'left': 'right', 'right': 'right'},
                            {'left': 'left', 'right': 'right'},
                            {'left': 'left'},
                            {'right': 'right'},
                            {'left': 'right'},
                            {'right': 'left'},
                            {'centerx': 'centerx'}
                            ]

        if horizontal_anchors in valid_anchor_set:
            return True
        elif len(horizontal_anchors) == 0:
            return False  # no horizontal anchors so just use defaults
        else:
            warnings.warn("Supplied horizontal anchors are invalid, defaulting to left", category=UserWarning)
            return False

    @staticmethod
    def _validate_vertical_anchors(anchors: Dict[str, Union[str, 'UIElement']]):
        # first make a dictionary of just the vertical anchors
        vertical_anchors = {}

        if 'top' in anchors:
            vertical_anchors.update({'top': anchors['top']})
        if 'bottom' in anchors:
            vertical_anchors.update({'bottom': anchors['bottom']})
        if 'centery' in anchors:
            vertical_anchors.update({'centery': anchors['centery']})

        valid_anchor_set = [{'top': 'top', 'bottom': 'top'},
                            {'top': 'bottom', 'bottom': 'bottom'},
                            {'top': 'top', 'bottom': 'bottom'},
                            {'top': 'top'},
                            {'bottom': 'bottom'},
                            {'top': 'bottom'},
                            {'bottom': 'top'},
                            {'centery': 'centery'}
                            ]

        if vertical_anchors in valid_anchor_set:
            return True
        elif len(vertical_anchors) == 0:
            return False  # no vertical anchors so just use defaults
        else:
            warnings.warn("Supplied vertical anchors are invalid, defaulting to top", category=UserWarning)
            return False

    def _setup_visibility(self, visible):
        if visible:
            self.visible = 1

        if self.ui_container is not None and not self.ui_container.visible:
            self.visible = 0

    def _setup_container(self, container):
        if container is None:
            # no container passed in so make it the root container
            if self.ui_manager.get_root_container() is not None:
                container = self.ui_manager.get_root_container()
            else:
                container = self
        elif not isinstance(container, IContainerLikeInterface):
            # oops, passed in something that wasn't a container so bail
            raise ValueError("container parameter must be of type "
                             "IContainerLikeInterface.")

        # by this point container should be a valid container
        self.ui_container = container.get_container()
        if self.ui_container is not None and self.ui_container is not self:
            self.ui_container.add_element(self)

    def get_focus_set(self) -> Set['UIElement']:
        return self._focus_set

    def set_focus_set(self, focus_set: Optional[Set['UIElement']]):
        if self.ui_manager.get_focus_set() is self._focus_set:
            self.ui_manager.set_focus_set(focus_set)
        self._focus_set = focus_set

    def join_focus_sets(self, element: 'UIElement'):
        if self._focus_set is not None:
            union_of_sets = set(self._focus_set | element.get_focus_set())
            for item in union_of_sets:
                item.set_focus_set(union_of_sets)

    def remove_element_from_focus_set(self, element):
        if self._focus_set is not None:
            self._focus_set.discard(element)

    def get_relative_rect(self) -> pygame.Rect:
        """
        The relative positioning rect.

        :return: A pygame rect.

        """
        return self.relative_rect

    def get_abs_rect(self) -> pygame.Rect:
        """
        The absolute positioning rect.

        :return: A pygame rect.

        """
        return self.rect

    def get_element_ids(self) -> List[str]:
        """
        A list of all the element IDs in this element's theming/event hierarchy.

        :return: a list of strings, one for each element in the hierarchy.
        """
        return self.element_ids

    def get_class_ids(self) -> List[str]:
        """
        A list of all the class IDs in this element's theming/event hierarchy.

        :return: a list of strings, one for each element in the hierarchy.
        """
        return self.class_ids

    def get_object_ids(self) -> List[str]:
        """
        A list of all the object IDs in this element's theming/event hierarchy.

        :return: a list of strings, one for each element in the hierarchy.
        """
        return self.object_ids

    def _create_valid_ids(self, container, parent_element, object_id, element_id):
        """
        Create valid IDs for the UI element.
        """
        if object_id is None:
            self.object_ids = []
        elif isinstance(object_id, ObjectID):
            self.object_ids = [object_id]
        else:
            self.object_ids = [ObjectID(id=object_id)]

    def _calc_top_offset(self) -> int:
        return (self.anchors['top_target'].get_abs_rect().bottom
                if 'top_target' in self.anchors
                else self.ui_container.get_abs_rect().top)

    def _calc_bottom_offset(self) -> int:
        return (self.anchors['bottom_target'].get_abs_rect().top
                if 'bottom_target' in self.anchors
                else self.ui_container.get_abs_rect().bottom)

    def _calc_centery_offset(self) -> int:
        return (self.anchors['centery_target'].get_abs_rect().centery
                if 'centery_target' in self.anchors
                else self.ui_container.get_abs_rect().centery)

    def _calc_left_offset(self) -> int:
        return (self.anchors['left_target'].get_abs_rect().right
                if 'left_target' in self.anchors
                else self.ui_container.get_abs_rect().left)

    def _calc_right_offset(self) -> int:
        return (self.anchors['right_target'].get_abs_rect().left
                if 'right_target' in self.anchors
                else self.ui_container.get_abs_rect().right)

    def _calc_centerx_offset(self) -> int:
        return (self.anchors['centerx_target'].get_abs_rect().centerx
                if 'centerx_target' in self.anchors
                else self.ui_container.get_abs_rect().centerx)

    def _update_absolute_rect_position_from_anchors(self, recalculate_margins=False):
        """
        Called when our element's relative position has changed.
        """
        new_top = 0
        new_bottom = 0
        top_offset = self._calc_top_offset()
        bottom_offset = self._calc_bottom_offset()

        center_x_and_y = False

        if 'center' in self.anchors:
            if self.anchors['center'] == 'center':
                center_x_and_y = True

        if ('centery' in self.anchors and self.anchors['centery'] == 'centery') or center_x_and_y:
            centery_offset = self._calc_centery_offset()
            new_top = self.relative_rect.top - self.relative_rect.height//2 + centery_offset
            new_bottom = self.relative_rect.bottom - self.relative_rect.height//2 + centery_offset

        if 'top' in self.anchors:
            if self.anchors['top'] == 'top':
                new_top = self.relative_rect.top + top_offset
                new_bottom = self.relative_rect.bottom + top_offset
            elif self.anchors['top'] == 'bottom':
                new_top = self.relative_rect.top + bottom_offset
                if self.relative_bottom_margin is None or recalculate_margins:
                    self.relative_bottom_margin = (bottom_offset -
                                                   (new_top + self.relative_rect.height))
                new_bottom = bottom_offset - self.relative_bottom_margin

        if 'bottom' in self.anchors:
            if self.anchors['bottom'] == 'top':
                new_top = self.relative_rect.top + top_offset
                new_bottom = self.relative_rect.bottom + top_offset
            elif self.anchors['bottom'] == 'bottom':
                if not ('top' in self.anchors and self.anchors['top'] == 'top'):
                    new_top = self.relative_rect.top + bottom_offset
                if self.relative_bottom_margin is None or recalculate_margins:
                    self.relative_bottom_margin = (bottom_offset -
                                                   (new_top + self.relative_rect.height))
                new_bottom = bottom_offset - self.relative_bottom_margin

        new_left = 0
        new_right = 0
        left_offset = self._calc_left_offset()
        right_offset = self._calc_right_offset()

        if ('centerx' in self.anchors and self.anchors['centerx'] == 'centerx') or center_x_and_y:
            centerx_offset = self._calc_centerx_offset()
            new_left = self.relative_rect.left - self.relative_rect.width//2 + centerx_offset
            new_right = self.relative_rect.right - self.relative_rect.width//2 + centerx_offset

        if 'left' in self.anchors:
            if self.anchors['left'] == 'left':
                new_left = self.relative_rect.left + left_offset
                new_right = self.relative_rect.right + left_offset
            elif self.anchors['left'] == 'right':
                new_left = self.relative_rect.left + right_offset
                if self.relative_right_margin is None or recalculate_margins:
                    self.relative_right_margin = (right_offset - (new_left + self.relative_rect.width))
                new_right = right_offset - self.relative_right_margin

        if 'right' in self.anchors:
            if self.anchors['right'] == 'left':
                new_left = self.relative_rect.left + left_offset
                new_right = self.relative_rect.right + left_offset
            elif self.anchors['right'] == 'right':
                if not ('left' in self.anchors and self.anchors['left'] == 'left'):
                    new_left = self.relative_rect.left + right_offset
                if self.relative_right_margin is None or recalculate_margins:
                    self.relative_right_margin = (right_offset - (new_left + self.relative_rect.width))
                new_right = right_offset - self.relative_right_margin

        self.rect.left = new_left
        self.rect.top = new_top
        new_height = new_bottom - new_top
        new_width = new_right - new_left
        new_width, new_height = self._get_clamped_to_minimum_dimensions((new_width, new_height))
        if (new_height != self.relative_rect.height) or (new_width != self.relative_rect.width):
            self.set_dimensions((new_width, new_height))

    def _update_relative_rect_position_from_anchors(self, recalculate_margins=False):
        """
        Called when our element's absolute position has been forcibly changed.
        """

        # This is a bit easier to calculate than getting the absolute position from the
        # relative one, because the absolute position rectangle is always relative to the top
        # left of the screen.

        # Setting these to None means we are always recalculating the margins in here.
        self.relative_bottom_margin = None
        self.relative_right_margin = None

        new_top = 0
        new_bottom = 0
        top_offset = self._calc_top_offset()
        bottom_offset = self._calc_bottom_offset()

        center_x_and_y = False
        if 'center' in self.anchors:
            if self.anchors['center'] == 'center':
                center_x_and_y = True

        if ('centery' in self.anchors and self.anchors['centery'] == 'centery') or center_x_and_y:
            centery_offset = self._calc_centery_offset()
            new_top = self.rect.top + self.relative_rect.height//2 - centery_offset
            new_bottom = self.rect.bottom + self.relative_rect.height//2 - centery_offset

        if 'top' in self.anchors:
            if self.anchors['top'] == 'top':
                new_top = self.rect.top - top_offset
                new_bottom = self.rect.bottom - top_offset
            elif self.anchors['top'] == 'bottom':
                new_top = self.rect.top - bottom_offset
                if self.relative_bottom_margin is None or recalculate_margins:
                    self.relative_bottom_margin = bottom_offset - self.rect.bottom
                new_bottom = self.rect.bottom - bottom_offset

        if 'bottom' in self.anchors:
            if self.anchors['bottom'] == 'top':
                new_top = self.rect.top - top_offset
                new_bottom = self.rect.bottom - top_offset
            elif self.anchors['bottom'] == 'bottom':
                if not ('top' in self.anchors and self.anchors['top'] == 'top'):
                    new_top = self.rect.top - bottom_offset
                if self.relative_bottom_margin is None or recalculate_margins:
                    self.relative_bottom_margin = bottom_offset - self.rect.bottom
                new_bottom = self.rect.bottom - bottom_offset

        new_left = 0
        new_right = 0
        left_offset = self._calc_left_offset()
        right_offset = self._calc_right_offset()

        if ('centerx' in self.anchors and self.anchors['centerx'] == 'centerx') or center_x_and_y:
            centerx_offset = self._calc_centerx_offset()
            new_left = self.rect.left + self.relative_rect.width//2 - centerx_offset
            new_right = self.rect.right + self.relative_rect.width//2 - centerx_offset

        if 'left' in self.anchors:
            if self.anchors['left'] == 'left':
                new_left = self.rect.left - left_offset
                new_right = self.rect.right - left_offset
            elif self.anchors['left'] == 'right':
                new_left = self.rect.left - right_offset
                if self.relative_right_margin is None or recalculate_margins:
                    self.relative_right_margin = right_offset - self.rect.right
                new_right = self.rect.right - right_offset

        if 'right' in self.anchors:
            if self.anchors['right'] == 'left':
                new_left = self.rect.left - left_offset
                new_right = self.rect.right - left_offset
            elif self.anchors['right'] == 'right':
                if not ('left' in self.anchors and self.anchors['left'] == 'left'):
                    new_left = self.rect.left - right_offset
                if self.relative_right_margin is None or recalculate_margins:
                    self.relative_right_margin = right_offset - self.rect.right
                new_right = self.rect.right - right_offset

        # set bottom and right first in case these are only anchors available
        self.relative_rect.bottom = new_bottom
        self.relative_rect.right = new_right

        # set top and left last to give these priority, in most cases where all anchors are set
        # we want relative_rect parameters to be correct for whatever the top & left sides are
        # anchored to. The data for the bottom and right in cases where left is anchored
        # differently to right and/or top is anchored differently to bottom should be captured by
        # the bottom and right margins.
        self.relative_rect.left = new_left
        self.relative_rect.top = new_top

    def _update_container_clip(self):
        """
        Creates a clipping rectangle for the element's image surface based on whether this
        element is inside its container, part-way in it, or all the way out of it.

        """
        if self.ui_container.get_image_clipping_rect() is not None:
            container_clip_rect = self.ui_container.get_image_clipping_rect().copy()
            container_clip_rect.left += self.ui_container.get_rect().left
            container_clip_rect.top += self.ui_container.get_rect().top
            if not container_clip_rect.contains(self.rect):
                left = max(0, container_clip_rect.left - self.rect.left)
                right = max(0, self.rect.width - max(0,
                                                     self.rect.right -
                                                     container_clip_rect.right))
                top = max(0, container_clip_rect.top - self.rect.top)
                bottom = max(0, self.rect.height - max(0,
                                                       self.rect.bottom -
                                                       container_clip_rect.bottom))
                clip_rect = pygame.Rect(left, top,
                                        max(0, right - left),
                                        max(0, bottom - top))
                self._clip_images_for_container(clip_rect)
            else:
                self._restore_container_clipped_images()

        elif not self.ui_container.get_rect().contains(self.rect):
            left = max(0, self.ui_container.get_rect().left - self.rect.left)
            right = max(0, self.rect.width - max(0,
                                                 self.rect.right -
                                                 self.ui_container.get_rect().right))
            top = max(0, self.ui_container.get_rect().top - self.rect.top)
            bottom = max(0, self.rect.height - max(0,
                                                   self.rect.bottom -
                                                   self.ui_container.get_rect().bottom))
            clip_rect = pygame.Rect(left, top,
                                    max(0, right - left),
                                    max(0, bottom - top))
            self._clip_images_for_container(clip_rect)
        else:
            self._restore_container_clipped_images()

    def update_containing_rect_position(self):
        """
        Updates the position of this element based on the position of it's container. Usually
        called when the container has moved.
        """
        self._update_absolute_rect_position_from_anchors()

        if self.drawable_shape is not None:
            self.drawable_shape.set_position(self.rect.topleft)

        self._update_container_clip()

    def set_relative_position(self, position: Union[pygame.math.Vector2,
                                                    Tuple[int, int],
                                                    Tuple[float, float]]):
        """
        Method to directly set the relative rect position of an element.

        :param position: The new position to set.

        """
        self.relative_rect.x = int(position[0])
        self.relative_rect.y = int(position[1])

        self._update_absolute_rect_position_from_anchors(recalculate_margins=True)

        if self.drawable_shape is not None:
            self.drawable_shape.set_position(self.rect.topleft)

        self._update_container_clip()
        self.ui_container.on_anchor_target_changed(self)

    def set_position(self, position: Union[pygame.math.Vector2,
                                           Tuple[int, int],
                                           Tuple[float, float]]):
        """
        Method to directly set the absolute screen rect position of an element.

        :param position: The new position to set.

        """
        self.rect.x = int(position[0])
        self.rect.y = int(position[1])
        self._update_relative_rect_position_from_anchors(recalculate_margins=True)

        if self.drawable_shape is not None:
            self.drawable_shape.set_position(self.rect.topleft)
        self._update_container_clip()
        self.ui_container.on_anchor_target_changed(self)

    def set_minimum_dimensions(self, dimensions: Union[pygame.math.Vector2,
                                                       Tuple[int, int],
                                                       Tuple[float, float]]):
        """
        If this window is resizable, then the dimensions we set here will be the minimum that
        users can change the window to. They are also used as the minimum size when
        'set_dimensions' is called.

        :param dimensions: The new minimum dimension for the window.

        """
        self.minimum_dimensions = (min(self.ui_container.rect.width, int(dimensions[0])),
                                   min(self.ui_container.rect.height, int(dimensions[1])))

        if ((self.rect.width < self.minimum_dimensions[0]) or
                (self.rect.height < self.minimum_dimensions[1])):
            new_width = max(self.minimum_dimensions[0], self.rect.width)
            new_height = max(self.minimum_dimensions[1], self.rect.height)
            self.set_dimensions((new_width, new_height))

    def set_dimensions(self, dimensions: Union[pygame.math.Vector2,
                                               Tuple[int, int],
                                               Tuple[float, float]],
                       clamp_to_container: bool = False):
        """
        Method to directly set the dimensions of an element.

        NOTE: Using this on elements inside containers with non-default anchoring arrangements
        may make a mess of them.

        :param dimensions: The new dimensions to set.
        :param clamp_to_container: Whether we should clamp the dimensions to the
                                   dimensions of the container or not.

        """
        dimensions = self._get_clamped_to_minimum_dimensions(dimensions, clamp_to_container)
        self.relative_rect.width = int(dimensions[0])
        self.relative_rect.height = int(dimensions[1])
        self.rect.size = self.relative_rect.size

        if dimensions[0] >= 0 and dimensions[1] >= 0:
            self._update_absolute_rect_position_from_anchors(recalculate_margins=True)

            if self.drawable_shape is not None:
                if self.drawable_shape.set_dimensions(self.relative_rect.size):
                    # needed to stop resizing 'lag'
                    self._set_image(self.drawable_shape.get_fresh_surface())

            self._update_container_clip()
            self.ui_container.on_anchor_target_changed(self)

def update(self, time_delta: float):
    """
    Update the UI element.
    """
    if not self.is_enabled:
        self.hovered = False
        self._hovering(False)
        return

    mouse_x, mouse_y = pygame.mouse.get_pos()

    if self.container:
        if self.container.rect.collidepoint(mouse_x, mouse_y):
            mouse_x -= self.container.rect.x
            mouse_y -= self.container.rect.y

    # Update text effect if active
    if self.active_text_effect is not None:
        self.active_text_effect.update(time_delta)

    # Call superclass update
    super().update(time_delta)

    # Check if mouse is over the element
    if self.rect.collidepoint(mouse_x, mouse_y):
        if not self.hovered:
            self._hovering(True)
            self.hovered = True
    else:
        if self.hovered:
            self._hovering(False)
            self.hovered = False


    def change_layer(self, new_layer: int):
        """
        Changes the layer this element is on.

        :param new_layer: The layer to change this element to.

        """
        if new_layer != self._layer:
            self.ui_group.change_layer(self, new_layer)
            self._layer = new_layer

    def kill(self):
        """
        Overriding regular sprite kill() method to remove the element from it's container.
        """
        if self.tool_tip is not None:
            self.tool_tip.kill()
        self.ui_container.remove_element(self)
        self.remove_element_from_focus_set(self)
        super().kill()

    def check_hover(self, time_delta: float, hovered_higher_element: bool) -> bool:
        """
        A method that helps us to determine which, if any, UI Element is currently being hovered
        by the mouse.

        :param time_delta: A float, the time in seconds between the last call to this function
                           and now (roughly).
        :param hovered_higher_element: A boolean, representing whether we have already hovered a
                                       'higher' element.

        :return bool: A boolean that is true if we have hovered a UI element, either just now or
                      before this method.
        """
        should_block_hover = False
        if self.alive():
            mouse_x, mouse_y = self.ui_manager.get_mouse_position()
            mouse_pos = pygame.math.Vector2(mouse_x, mouse_y)

            if (self.hover_point(mouse_x, mouse_y) and
                    not hovered_higher_element):
                should_block_hover = True

                if self.can_hover():
                    if not self.hovered:
                        self.hovered = True
                        self.on_hovered()

                    self.while_hovering(time_delta, mouse_pos)
                else:
                    if self.hovered:
                        self.hovered = False
                        self.on_unhovered()
            else:
                if self.hovered:
                    self.hovered = False
                    self.on_unhovered()
        elif self.hovered:
            self.hovered = False
        return should_block_hover

    def on_fresh_drawable_shape_ready(self):
        """
        Called when our drawable shape has finished rebuilding the active surface. This is needed
        because sometimes we defer rebuilding until a more advantageous (read quieter) moment.
        """
        self._set_image(self.drawable_shape.get_fresh_surface())

    def on_hovered(self):
        """
        Called when this UI element first enters the 'hovered' state.
        """
        self.hover_time = 0.0

    def on_unhovered(self):
        """
        Called when this UI element leaves the 'hovered' state.
        """
        if self.tool_tip is not None:
            self.tool_tip.kill()
            self.tool_tip = None

    def while_hovering(self, time_delta: float,
                       mouse_pos: Union[pygame.math.Vector2, Tuple[int, int], Tuple[float, float]]):
        """
        Called while we are in the hover state. It will create a tool tip if we've been in the
        hover state for a while, the text exists to create one and we haven't created one already.

        :param time_delta: Time in seconds between calls to update.
        :param mouse_pos: The current position of the mouse.

        """
        if (self.tool_tip is None and self.tool_tip_text is not None and
                self.hover_time > self.tool_tip_delay):
            hover_height = int(self.rect.height / 2)
            self.tool_tip = self.ui_manager.create_tool_tip(text=self.tool_tip_text,
                                                            position=(mouse_pos[0],
                                                                      self.rect.centery),
                                                            hover_distance=(0,
                                                                            hover_height),
                                                            parent_element=self,
                                                            object_id=self.tool_tip_object_id,
                                                            wrap_width=self.tool_tip_wrap_width,
                                                            text_kwargs=self.tool_tip_text_kwargs)

        self.hover_time += time_delta

    def can_hover(self) -> bool:
        """
        A stub method to override. Called to test if this method can be hovered.
        """
        return self.alive()

    def hover_point(self, hover_x: float, hover_y: float) -> bool:
        """
        Test if a given point counts as 'hovering' this UI element. Normally that is a
        straightforward matter of seeing if a point is inside the rectangle. Occasionally it
        will also check if we are in a wider zone around a UI element once it is already active,
        this makes it easier to move scroll bars and the like.

        :param hover_x: The x (horizontal) position of the point.
        :param hover_y: The y (vertical) position of the point.

        :return: Returns True if we are hovering this element.

        """

        container_clip_rect = self.ui_container.get_rect().copy()
        if self.ui_container.get_image_clipping_rect() is not None:
            container_clip_rect.size = self.ui_container.get_image_clipping_rect().size
            container_clip_rect.left += self.ui_container.get_image_clipping_rect().left
            container_clip_rect.top += self.ui_container.get_image_clipping_rect().top

        if self.drawable_shape is not None:
            return (self.drawable_shape.collide_point((hover_x, hover_y)) and
                    bool(container_clip_rect.collidepoint(hover_x, hover_y)))

        return (bool(self.rect.collidepoint(hover_x, hover_y)) and
                bool(container_clip_rect.collidepoint(hover_x, hover_y)))

    # pylint: disable=unused-argument,no-self-use
    def process_event(self, event: pygame.event.Event) -> bool:
        """
        A stub to override. Gives UI Elements access to pygame events.

        :param event: The event to process.

        :return: Should return True if this element makes use of this event.

        """
        return False

    def focus(self):
        """
        A stub to override. Called when we focus this UI element.
        """
        self.is_focused = True

    def unfocus(self):
        """
        A stub to override. Called when we stop focusing this UI element.
        """
        self.is_focused = False

    def rebuild_from_changed_theme_data(self):
        """
        A stub to override when we want to rebuild from theme data.
        """
        # self.combined_element_ids = self.ui_theme.build_all_combined_ids(self.element_ids,
        #                                                                  self.object_ids)

    def rebuild(self):
        """
        Takes care of rebuilding this element. Most derived elements are going to override this,
        and hopefully call the super() class method.

        """
        if self._visual_debug_mode:
            self._set_image(self.pre_debug_image)
            self.pre_debug_image = None

    def set_visual_debug_mode(self, activate_mode: bool):
        """
        Enables a debug mode for the element which displays layer information on top of it in
        a tiny font.

        :param activate_mode: True or False to enable or disable the mode.

        """
        if activate_mode:
            default_font = self.ui_manager.get_theme().get_font_dictionary().get_default_font()
            layer_text_render = render_white_text_alpha_black_bg(default_font,
                                                                 "UI Layer: " + str(self._layer))

            if self.image is not None:
                self.pre_debug_image = self.image.copy()
                # check if our surface is big enough to hold the debug info,
                # if not make a new, bigger copy
                make_new_larger_surface = False
                surf_width = self.image.get_width()
                surf_height = self.image.get_height()
                if self.image.get_width() < layer_text_render.get_width():
                    make_new_larger_surface = True
                    surf_width = layer_text_render.get_width()
                if self.image.get_height() < layer_text_render.get_height():
                    make_new_larger_surface = True
                    surf_height = layer_text_render.get_height()

                if make_new_larger_surface:
                    new_surface = pygame.surface.Surface((surf_width, surf_height),
                                                         flags=pygame.SRCALPHA,
                                                         depth=32)
                    basic_blit(new_surface, self.image, (0, 0))
                    self._set_image(new_surface)
                basic_blit(self.image, layer_text_render, (0, 0))
            else:
                self._set_image(layer_text_render)
            self._visual_debug_mode = True
        else:
            self.rebuild()
            self._visual_debug_mode = False

    def _clip_images_for_container(self, clip_rect: Union[pygame.Rect, None]):
        """
        Set the current image clip based on the container.

        :param clip_rect: The clipping rectangle.

        """
        self._set_image_clip(clip_rect)

    def _restore_container_clipped_images(self):
        """
        Clear the image clip.

        """
        self._set_image_clip(None)

    def _set_image_clip(self, rect: Union[pygame.Rect, None]):
        """
        Sets a clipping rectangle on this element's image determining what portion of it will
        actually be displayed when this element is blitted to the screen.

        :param rect: A clipping rectangle, or None to clear the clip.

        """
        if rect is not None:
            rect.width = max(rect.width, 0)
            rect.height = max(rect.height, 0)

            if self._pre_clipped_image is None and self.image is not None:
                self._pre_clipped_image = self.image.copy()

            self._image_clip = rect
            if self.image is not None:
                if self.image.get_size() != self._pre_clipped_image.get_size():
                    self.image = pygame.Surface(self._pre_clipped_image.get_size(), flags=pygame.SRCALPHA, depth=32)
                self.image.fill(pygame.Color('#00000000'))
                basic_blit(self.image, self._pre_clipped_image, self._image_clip, self._image_clip)

        elif self._image_clip is not None:
            self._image_clip = None
            self._set_image(self._pre_clipped_image)
        else:
            self._image_clip = None

    def get_image_clipping_rect(self) -> Union[pygame.Rect, None]:
        """
        Obtain the current image clipping rect.

        :return: The current clipping rect. May be None.

        """
        return self._image_clip

    def set_image(self, new_image: Union[pygame.surface.Surface, None]):
        """
        This used to be the way to set the proper way to set the .image property of a UIElement (inherited from
        pygame.Sprite), but it is intended for internal use in the library - not for adding actual images/pictures
        on UIElements. As such I've renamed the original function to make it protected and not part of the interface
        and deprecated this one for most elements.

        :return:
        """
        warnings.warn("This method will be removed for "
                      "most elements from version 0.8.0", DeprecationWarning, stacklevel=2)
        self._set_image(new_image)

    def _set_image(self, new_image: Union[pygame.surface.Surface, None]):
        """
        Wraps setting the image variable of this element so that we also set the current image
        clip on the image at the same time.

        :param new_image: The new image to set.

        """
        if self.get_image_clipping_rect() is not None and new_image is not None:
            self._pre_clipped_image = new_image
            if (self.get_image_clipping_rect().width == 0 and
                    self.get_image_clipping_rect().height == 0):
                self.image = self.ui_manager.get_universal_empty_surface()
            else:
                self.image = pygame.surface.Surface(self._pre_clipped_image.get_size(),
                                                    flags=pygame.SRCALPHA,
                                                    depth=32)
                self.image.fill(pygame.Color('#00000000'))
                basic_blit(self.image,
                           self._pre_clipped_image,
                           self.get_image_clipping_rect(),
                           self.get_image_clipping_rect())
        else:
            self.image = new_image.copy() if new_image is not None else None
            self._pre_clipped_image = None

    def get_top_layer(self) -> int:
        """
        Assuming we have correctly calculated the 'thickness' of it, this method will
        return the top of this element.

        :return int: An integer representing the current highest layer being used by this element.

        """
        return self._layer + self.layer_thickness

    def get_starting_height(self) -> int:
        """
        Get the starting layer height of this element. (i.e. the layer we start placing it on
        *above* it's container, it may use more layers above this layer)

        :return: an integer representing the starting layer height.

        """
        return self.starting_height

    def _check_shape_theming_changed(self, defaults: Dict[str, Any]) -> bool:
        """
        Checks all the standard miscellaneous shape theming parameters.

        :param defaults: A dictionary of default values
        :return: True if any have changed.
        """
        has_any_changed = False

        if self._check_misc_theme_data_changed('border_width', defaults['border_width'], int):
            has_any_changed = True

        if self._check_misc_theme_data_changed('shadow_width', defaults['shadow_width'], int):
            has_any_changed = True

        if self._check_misc_theme_data_changed('shape_corner_radius',
                                               defaults['shape_corner_radius'], int):
            has_any_changed = True

        return has_any_changed

    def _check_misc_theme_data_changed(self,
                                       attribute_name: str,
                                       default_value: Any,
                                       casting_func: Callable[[Any], Any],
                                       allowed_values: Union[List, None] = None) -> bool:
        """
        Checks if the value of a pieces of miscellaneous theming data has changed, and if it has,
        updates the corresponding attribute on the element and returns True.

        :param attribute_name: The name of the attribute.
        :param default_value: The default value for the attribute.
        :param casting_func: The function to cast to the type of the data.

        :return: True if the attribute has changed.

        """
        has_changed = False
        attribute_value = default_value
        try:
            attribute_value = casting_func(
                self.ui_theme.get_misc_data(attribute_name, self.combined_element_ids))
        except (LookupError, ValueError):
            attribute_value = default_value
        finally:
            if allowed_values and attribute_value not in allowed_values:
                attribute_value = default_value

            if attribute_value != getattr(self, attribute_name, default_value):
                setattr(self, attribute_name, attribute_value)
                has_changed = True
        return has_changed

    def disable(self):
        """
        Disables elements so they are no longer interactive.
        This is just a default fallback implementation for elements that don't define their own.

        Elements should handle their own enabling and disabling.
        """
        self.is_enabled = False

    def enable(self):
        """
        Enables elements so they are interactive again.
        This is just a default fallback implementation for elements that don't define their own.

        Elements should handle their own enabling and disabling.
        """
        self.is_enabled = True

    def show(self):
        """
        Shows the widget, which means the widget will get drawn and will process events.
        """
        self.visible = 1

    def hide(self):
        """
        Hides the widget, which means the widget will not get drawn and will not process events.
        Clear hovered state.
        """
        self.visible = 0

        self.hovered = False
        self.hover_time = 0.0

    def _get_appropriate_state_name(self):
        """
        Returns a string representing the appropriate state for the widgets DrawableShapes.
        Currently only returns either 'normal' or 'disabled' based on is_enabled.
        """

        if self.is_enabled:
            return "normal"
        return "disabled"

    def on_locale_changed(self):
        pass

    def get_anchor_targets(self) -> list:
        targets = []
        if 'left_target' in self.anchors:
            targets.append(self.anchors['left_target'])
        if 'right_target' in self.anchors:
            targets.append(self.anchors['right_target'])
        if 'top_target' in self.anchors:
            targets.append(self.anchors['top_target'])
        if 'bottom_target' in self.anchors:
            targets.append(self.anchors['bottom_target'])

        return targets

    @staticmethod
    def tuple_extract(str_data: str) -> Tuple[int, int]:
        # Used for parsing coordinate tuples in themes.
        x, y = str_data.split(',')
        return int(x), int(y)

    def update_theming(self, new_theming_data: str):
        """
        Update the theming for this element using the most specific ID assigned to it.

        If you have not given this element a unique ID, this function will also update the theming of other elements
        of this theming class or of this element type.

        :param new_theming_data: the new theming data in a json string
        """
        self.ui_theme.update_single_element_theming(self.most_specific_combined_id, new_theming_data)
        self.rebuild_from_changed_theme_data()

    def set_tooltip(self, text: Optional[str] = None, object_id: Optional[ObjectID] = None,
                    text_kwargs: Optional[Dict[str, str]] = None, delay: Optional[float] = None,
                    wrap_width: Optional[int] = None):
        self.tool_tip_text = text
        self.tool_tip_text_kwargs = {}
        if text_kwargs is not None:
            self.tool_tip_text_kwargs = text_kwargs
        self.tool_tip_object_id = object_id

        if delay is not None:
            self.tool_tip_delay = delay

        self.tool_tip_wrap_width = wrap_width

