import ctypes
from OpenGL import GL as gl
from PIL import Image
import sdl2
from shader_filters import *
import random

DEF_WINDOW_WIDTH = 1024
DEF_WINDOW_HEIGHT = 768


class View:
    """
    Holds coordinates for navigating ortho view
    """
    offset = (0.0, 0.0)

    zoom = 1

    def reset(self):
        self.offset = (0.0, 0.0)
        self.zoom = 1


class Console:
    """
    Hold logic for dealing with console input and output
    """
    console_prompt = ">"

    input_buffer = []

    output_buffer = []

    current_input = ""

    max_buffer_len = 100

    line_number = 0

    console_filter = None

    def cleanup(self):
        if self.console_filter:
            self.console_filter.cleanup_shader()
            self.console_filter = None

    def _create_shader(self):
        if not self.console_filter:
            offset = (0, 0)
            self.console_filter = ConsoleFilter()
            self.console_filter.add_str(self.console_prompt, offset)

    def render(self, window_dimensions):
        self._create_shader()
        offset = (0, 0)
        self.console_filter.render(offset, window_dimensions)

    def clear(self):
        self.line_number = 0
        self.output_buffer = []
        self.console_filter.clear()
        offset = (0, 0)
        self.console_filter.add_str(self.console_prompt, offset)

    def get_formatted_input(self, text):
        return "%s%s" % (self.console_prompt, text)

    def add_input(self, text):
        self._create_shader()
        self.input_buffer = [text] + \
            self.input_buffer[:self.max_buffer_len - 1]
        self.add_output(self.get_formatted_input(text), update_filter=False)

    def add_output(self, text, update_filter=True, update_line_number=True):
        for t in text.split("\n"):
            if update_line_number:
                self.line_number += 1
            if update_filter:
                self.console_filter.backspace(len(self.get_input()))
                self.console_filter.add_str(
                    "%s\n%s" % (t, self.get_input()), (0, 0))
            self.output_buffer = [t] + \
                self.output_buffer[:self.max_buffer_len - 1]

    def get_output(self, num_lines):
        return self.output_buffer[:num_lines]

    def get_input(self):
        return self.get_formatted_input(self.current_input)

    def backspace(self):
        if self.current_input:
            self.console_filter.backspace()
            self.current_input = self.current_input[:-1]

    def parse_input(self, text):
        """
        returns any commands that are detected, keeps track of input
        and updates output
        """
        inputted_commands = []
        txt = text

        self._create_shader()
        # Seems like first time console is opened the backquote is added
        # to input so for now manually removing it until I find out cause
        txt = txt.replace('`', '')

        char_width = self.console_filter.img_dimensions[0] / 16

        while '\n' in txt:
            txt_split = txt.split('\n', 1)
            self.current_input += txt_split[0]
            self.add_input(self.current_input)
            curr_offset = len(self.get_input())-len(txt_split[0])
            coords = ((len(self.console_prompt)+curr_offset) * char_width, 0)
            self.console_filter.add_str(txt_split[0], coords)
            self.console_filter.add_str("\n%s" % (self.console_prompt), (0, 0))
            inputted_commands.append(self.current_input)
            self.current_input = ""
            txt = txt_split[1]
        self.current_input += txt
        curr_offset = len(self.current_input) - len(txt)
        coords = ((len(self.console_prompt)+curr_offset) * char_width, 0)
        self.console_filter.add_str(txt, coords)

        return inputted_commands


class ImageGlitch:
    """
    Image glitching class, uses opengl shaders to filters images. SDL2 window
    and opengl context can be created using this class
    """
    fb_ids = {
        "a": -1,
        "b": -1,
    }

    target_texture = -1

    target_fb = -1

    fb_texture_map = {
        "a": "fb_tex",
        "b": "fb_tex_alt",
    }

    texture_ids = {
        "img": -1,
        "fb_tex": -1,
        "fb_tex_alt": -1,
    }

    img_dimensions = (-1, -1)

    view = View()

    window = None

    window_dimensions = (DEF_WINDOW_WIDTH, DEF_WINDOW_HEIGHT)

    all_filters = {}

    filters = []

    final_filter = None

    console = Console()

    console_enabled = False

    frame = 0

    playing = False

    recording = False

    recording_remaining_frames = -1

    recording_frame_num = -1

    fps = 10

    last_update = sdl2.SDL_GetTicks()

    def __init__(self):
        self.init_sdl()
        self.all_filters = {k: v() for k, v in ALL_FILTERS.iteritems()}

    def filter_img(self, img, filters):
        """
        this should destroy any existing resources if they exist, then
        init program for new image
        """
        self.cleanup_img_fb()
        self.cleanup_image_texture()

        self.img_dimensions = img.size

        assert all(name in self.all_filters for name in filters), (
            "Error, filter not found")

        self.filters = [self.all_filters[n] for n in filters]
        if not self.final_filter:
            self.final_filter = OrthoFilter()

        self.init_image_texture(img)
        self.init_img_fb()

        self.update_filtered_image(update_frame_count=False)

    def init_sdl(self):
        """
        Create a window and initialize opengl
        """
        sdl2.SDL_Init(sdl2.SDL_INIT_EVERYTHING)
        sdl2.SDL_GL_SetAttribute(sdl2.SDL_GL_CONTEXT_MAJOR_VERSION, 3)
        sdl2.SDL_GL_SetAttribute(sdl2.SDL_GL_CONTEXT_MINOR_VERSION, 2)
        sdl2.SDL_GL_SetAttribute(sdl2.SDL_GL_CONTEXT_PROFILE_MASK,
                                 sdl2.SDL_GL_CONTEXT_PROFILE_CORE)
        sdl2.SDL_GL_SetAttribute(sdl2.SDL_GL_DOUBLEBUFFER, 1)
        sdl2.SDL_GL_SetAttribute(sdl2.SDL_GL_DEPTH_SIZE, 24)
        sdl2.SDL_GL_SetSwapInterval(0)  # 0 = no vsync
        self.window = sdl2.SDL_CreateWindow(
            "DPT GLITCH GUY",
            sdl2.SDL_WINDOWPOS_UNDEFINED,
            sdl2.SDL_WINDOWPOS_UNDEFINED,
            DEF_WINDOW_WIDTH,
            DEF_WINDOW_HEIGHT,
            sdl2.SDL_WINDOW_OPENGL | sdl2.SDL_WINDOW_SHOWN)
        assert self.window, "Error: Could not create window"
        sdl2.SDL_SetWindowResizable(self.window, True)
        glcontext = sdl2.SDL_GL_CreateContext(self.window)
        gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
        gl.glEnable(gl.GL_CULL_FACE)
        gl.glEnable(gl.GL_BLEND)
        gl.glClearColor(0.6, 0.6, 0.6, 0.0)

    def cleanup_img_fb(self):
        """
        Destroy any allocated framebuffers
        """
        for k, v in self.fb_ids.iteritems():
            if v != -1:
                gl.glDeleteFramebuffers(1, int(v))
                self.fb_ids[k] = -1

    def init_img_fb(self):
        """
        Create 2 framebuffers to use for swapping image to texture for post
        processing shaders
        """
        for name in self.fb_ids:
            self.fb_ids[name] = gl.glGenFramebuffers(1)
            gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, self.fb_ids[name])
            gl.glFramebufferTexture2D(
                gl.GL_FRAMEBUFFER,
                gl.GL_COLOR_ATTACHMENT0,
                gl.GL_TEXTURE_2D,
                self.texture_ids[
                    self.fb_texture_map[name]],
                0)

            assert (gl.GL_FRAMEBUFFER_COMPLETE ==
                    gl.glCheckFramebufferStatus(gl.GL_FRAMEBUFFER)), (
                "Frame buffer %s isn't completely initialized" % (name))

        gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, 0)

    def cleanup_image_texture(self):
        """
        Cleanup allocated textures
        """
        for k, v in self.texture_ids.iteritems():
            if v != -1:
                gl.glDeleteTextures(v)
                self.texture_ids[k] = -1

    def init_image_texture(self, img):
        """
        allocate textures that are the size of the imported image. One will be
        attached to a framebuffer.
        """
        image_bytes = img.convert("RGBA").tobytes("raw", "RGBA", 0, -1)
        for name in self.texture_ids:
            self.texture_ids[name] = gl.glGenTextures(1)
            gl.glBindTexture(gl.GL_TEXTURE_2D, self.texture_ids[name])
            gl.glTexParameterf(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER,
                               gl.GL_NEAREST)
            gl.glTexParameterf(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER,
                               gl.GL_NEAREST)

            gl.glPixelStorei(gl.GL_UNPACK_ALIGNMENT, 1)

            gl.glTexImage2D(
                gl.GL_TEXTURE_2D,
                0,
                gl.GL_RGBA8,
                img.size[0],
                img.size[1],
                0,
                gl.GL_RGBA,
                gl.GL_UNSIGNED_BYTE,
                image_bytes)

    def record(self, folder_name="mov"):
        """
        """
        filename = "%s/%03d.png" % (folder_name, self.recording_frame_num)
        self.console.add_output(
            "Saved frame %s/%s" %
            (self.recording_frame_num +
             1,
             self.recording_frame_num +
             self.recording_remaining_frames))
        self.recording_frame_num += 1
        self.recording_remaining_frames -= 1
        if self.recording_remaining_frames <= 0:
            self.console.add_output("Done recording")
            self.recording = False
            self.recording_frame_num = 0
            self.recording_remaining_frames = -1
        image = self.get_filter_img()
        image.save(filename, compress_level=3)
        image.close()

    def get_filter_img(self):
        width = self.img_dimensions[0]
        height = self.img_dimensions[1]
        gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, self.target_fb)
        gl.glReadBuffer(gl.GL_COLOR_ATTACHMENT0)
        pixels = gl.glReadPixels(
            0, 0, width, height, gl.GL_RGBA, gl.GL_UNSIGNED_BYTE)
        #gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, 0)
        image = Image.frombytes("RGBA", (width, height), pixels)
        image = image.transpose(Image.FLIP_TOP_BOTTOM)
        return image

    def screenshot(self, filename):
        """
        bind the last framebuffer used during filtering and copy pixels to
        image and save as filename
        """
        image = self.get_filter_img()
        image.save(filename, compress_level=3)

    def update_filtered_image(self, update_frame_count=True):
        """
        Update the image by processing it with all of the shaders.
        """
        gl.glBindTexture(gl.GL_TEXTURE_2D, self.texture_ids['img'])
        current_fb = [(x, y) for x, y in self.fb_texture_map.iteritems()]
        for val in self.filters:
            gl.glBindFramebuffer(
                gl.GL_FRAMEBUFFER, self.fb_ids[current_fb[0][0]])
            gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)
            val.render(self.img_dimensions, self.frame)
            gl.glBindTexture(gl.GL_TEXTURE_2D, self.texture_ids[
                             current_fb[0][1]])
            self.target_texture = self.texture_ids[current_fb[0][1]]
            self.target_fb = self.fb_ids[current_fb[0][0]]
            current_fb = current_fb[1:] + current_fb[:1]
        if update_frame_count:
            self.frame += 1
            if self.recording:
                self.record()
        #gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, 0)

    def update_screen(self):
        """
        Updates what is on the screen.
        """
        gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, 0)

        # This renders the filters into an orho view to allow
        # scaling and offseting for preview
        tar_tex = self.target_texture if self.filters else self.texture_ids[
            'img']
        gl.glBindTexture(gl.GL_TEXTURE_2D, tar_tex)
        self.final_filter.render(self.view.offset, self.view.zoom,
                                 self.window_dimensions, self.img_dimensions)

        # This renders the console
        if self.console_enabled:
            self.console.render(self.window_dimensions)

        sdl2.SDL_GL_SwapWindow(self.window)

    def handle_resize(self, dimensions):
        """
        Called when the window is resized
        """
        self.window_dimensions = dimensions

    def do_command(self, cmd):
        update_image = False
        update_screen = False
        update_frame_count = False
        cmd = cmd.strip()
        if not cmd:
            return False, True, False
        if cmd == 'clear':
            self.console.clear()
            update_screen = True
        elif cmd == 'shuffle':
            random.shuffle(self.filters)
            update_screen = True
            update_image = True
            self.console.add_output("Filter order shuffled.")
        elif cmd == 'all':
            self.console.add_output(
                "%s" % ("\n".join(sorted([name for name in ALL_FILTERS]))))
            update_screen = True
        elif cmd == 'help':
            self.console.add_output("You are on your own ;(")
            update_screen = True
        elif cmd[:5] == 'echo ':
            self.console.add_output(cmd[5:])
            update_screen = True
        elif cmd[:4] == 'add ':
            target = cmd[4:]

            if target in self.all_filters:
                self.filters.append(self.all_filters[target])
                self.console.add_output("Success adding filter %s." % (target))
                update_image = True
            else:
                self.console.add_output("Could not find filter %s." % (target))
            update_screen = True
        elif cmd[:4] == 'mov ':
            targets = cmd[4:].split(' ')
            target_x = None
            target_y = None
            try:
                target_x = int(targets[0])
                target_y = int(targets[1])
            except:
                self.console.add_output("Failed to parse int!")
            if target_x is not None and target_y is not None:
                if target_x < 0 or target_x >= len(self.filters):
                    self.console.add_output("Target x is out of bounds!")
                if target_y < 0 or target_y >= len(self.filters):
                    self.console.add_output("Target y is out of bounds!")
                    target_x = target_y
                self.console.add_output(
                    "Success, switched %s and %s." % (target_x, target_y))
                if target_x != target_y:
                    tmp = self.filters[target_y]
                    self.filters[target_y] = self.filters[target_x]
                    self.filters[target_x] = tmp
                    update_image = True
            update_screen = True
        elif cmd[:5] == 'load ':
            target = cmd[5:]
            img = None
            try:
                img = Image.open(target)
            except:
                self.console.add_output("Could not load image %s" % (target))
            if img is not None:
                filters = [k for k, v in self.all_filters.iteritems()
                           for f in self.filters if v == f]
                self.filter_img(img, filters)
                img.close()
                self.console.add_output("Success, loaded image %s" % (target))
            update_screen = True
        elif cmd[:7] == 'record ':
            num_frames = None
            try:
                num_frames = int(cmd[7:])
            except:
                self.console.add_output("Failed to parse int")

            if num_frames is not None:
                self.console.add_output("Recording %s frames." % (num_frames))
                self.recording = True
                self.recording_remaining_frames = num_frames
                self.recording_frame_num = 0
            update_screen = True
        elif cmd[:4] == 'rem ':
            target = None
            if cmd[4:] == 'all':
                self.filters = []
                self.console.add_output("Success.")
                update_image = True
            else:
                try:
                    target = int(cmd[4:])
                except:
                    self.console.add_output("Could not parse int!")
                if target is not None:
                    if target < 0 or target > len(self.filters):
                        self.console.add_output("That index is out of bounds!")
                    else:
                        self.console.add_output("Success.")
                        self.filters = self.filters[
                            :target] + self.filters[target + 1:]
                        update_image = True
            update_screen = True
        elif cmd == 'list':
            for i in range(len(self.filters)):
                self.console.add_output("%d %s" % (i, str(self.filters[i])))
            update_screen = True
        elif cmd == 'next':
            self.console.add_output('Success.')
            update_image = True
            update_screen = True
            update_frame_count = True
        elif cmd == 'play':
            self.playing = True
            self.console.add_output("Success. Playing: %s" % self.playing)
            update_screen = True
        elif cmd == 'screenshot':
            self.screenshot('out.png')
            self.console.add_output("Success, saved out.png.")
            update_screen = True
        elif cmd == 'stop':
            self.playing = False
            self.console.add_output("Success: Playing: %s" % self.playing)
            update_screen = True
        else:
            self.console.add_output("Command not recognized.")
            update_screen = True
        return update_image, update_screen, update_frame_count

    def run(self):
        run, update_img, update_view, update_frame = self.poll_events()

        if (run and self.playing and
                sdl2.SDL_GetTicks() - self.last_update > 1000 / self.fps):
            self.update_filtered_image()
            self.last_update = sdl2.SDL_GetTicks()
            self.update_screen()
        else:
            if update_img:
                self.update_filtered_image(
                    update_frame_count=update_frame)
            if update_view:
                self.update_screen()

        delay = 10
        sdl2.SDL_Delay(delay)
        return run

    def poll_events(self):
        """
        Wait for a SDL2 event, handle it once encountered
        """
        update_img = False
        update_view = False
        update_frame = False
        event = sdl2.SDL_Event()
        while sdl2.SDL_PollEvent(ctypes.byref(event)):
            # resize events
            if event.type == sdl2.SDL_WINDOWEVENT:
                if event.window.event == sdl2.SDL_WINDOWEVENT_RESIZED:
                    self.handle_resize(
                        (event.window.data1, event.window.data2))
                if event.window.event in [sdl2.SDL_WINDOWEVENT_RESIZED,
                                          sdl2.SDL_WINDOWEVENT_EXPOSED]:
                    update_view = True
            # quit events
            if event.type == sdl2.SDL_QUIT:
                return False, False, False, False

            # Console inputs
            if self.console_enabled:
                commands = []
                if event.type == sdl2.SDL_TEXTINPUT:
                    event_str = event.text.text[:]
                    commands += self.console.parse_input(event_str)
                    update_view = True
                if event.type == sdl2.events.SDL_KEYDOWN:
                    if event.key.keysym.sym == sdl2.SDLK_BACKSPACE:
                        self.console.backspace()
                        update_view = True
                    elif event.key.keysym.sym == sdl2.SDLK_RETURN:
                        commands += self.console.parse_input('\n')
                        update_view = True
                for cmd in commands:
                    update_img, update_view, update_frame = self.do_command(
                        cmd)

            # hotkeys
            if event.type == sdl2.events.SDL_KEYDOWN:
                if event.key.keysym.sym == sdl2.SDLK_ESCAPE:
                    return False, False, False, False
                elif event.key.keysym.sym == sdl2.SDLK_BACKQUOTE:
                    self.console_enabled = not self.console_enabled
                    if self.console_enabled:
                        sdl2.SDL_StartTextInput()
                    else:
                        sdl2.SDL_StopTextInput()
                    update_view = True
                if self.console_enabled:
                    return True, update_img, update_view, update_frame
                if event.key.keysym.sym == sdl2.SDLK_a:
                    self.playing = True
                    update_view = True
                    update_img = True
                elif event.key.keysym.sym == sdl2.SDLK_s:
                    self.playing = False
                    update_view = True
                    update_img = True
                elif event.key.keysym.sym == sdl2.SDLK_r:
                    random.shuffle(self.filters)
                    update_img = True
                    update_view = True
                elif event.key.keysym.sym == sdl2.SDLK_UP:
                    self.view.offset = (
                        self.view.offset[0], self.view.offset[1] - 8)
                    update_view = True
                elif event.key.keysym.sym == sdl2.SDLK_DOWN:
                    self.view.offset = (
                        self.view.offset[0], self.view.offset[1] + 8)
                    update_view = True
                elif event.key.keysym.sym == sdl2.SDLK_LEFT:
                    self.view.offset = (
                        self.view.offset[0] + 8, self.view.offset[1])
                    update_view = True
                elif event.key.keysym.sym == sdl2.SDLK_RIGHT:
                    self.view.offset = (
                        self.view.offset[0] - 8, self.view.offset[1])
                    update_view = True
                elif event.key.keysym.sym == sdl2.SDLK_EQUALS:
                    self.view.zoom += 0.05
                    update_view = True
                elif event.key.keysym.sym == sdl2.SDLK_MINUS:
                    self.view.zoom -= 0.05
                    update_view = True

        return True, update_img, update_view, update_frame

    def cleanup(self):
        """
        destroys opengl and sdl resources allocated
        """
        for val in self.all_filters.itervalues():
            val.cleanup_shader()
        self.filters = []
        if self.final_filter:
            self.final_filter.cleanup_shader()
        if self.console:
            self.console.cleanup()
        self.final_filter = None
        self.cleanup_img_fb()
        self.cleanup_image_texture()
        if self.window:
            sdl2.SDL_DestroyWindow(self.window)
            self.window = None
        self.view.reset()

    def __del__(self):
        self.cleanup()


if __name__ == "__main__":
    img = Image.open('selena.jpg')
    ig = ImageGlitch()

    import atexit
    atexit.register(ig.cleanup)

    ig.filter_img(img,
                  [
                      'first',
                      # 'second',
                      # 'third',
                      'rgb_shift',
                      # 'repeat_end',
                      # 'static',
                      # 'static2',
                      'scanlines',
                  ])

    img.close()
    running = True
    ig.update_screen()

    while running:
        running = ig.run()
