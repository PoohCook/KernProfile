#Author-Pooh
#Description-

import adsk.core, adsk.fusion, adsk.cam, traceback

_app = None
_ui  = None
_handlers = []

class MySelectHandler(adsk.core.SelectionEventHandler):
    def __init__(self):
        super().__init__()
    def notify(self, args):
        global _app, _ui
        try:
            profile = adsk.fusion.Profile.cast(args.selection.entity)
            
        except:
            if _ui:
                _ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))

# Event handler that reacts to when the command is destroyed. This terminates the script.            
class MyCommandExecuteHandler(adsk.core.CommandEventHandler):
    def __init__(self):
        super().__init__()
    def pLoopDetails(self, ploop):
        msg = "\n%s: %s" % (
            "outer" if ploop.isOuter else "inner",
            ploop.parentProfile.areaProperties().area
        )

        for j in range(ploop.profileCurves.count):
            curve = ploop.profileCurves.item(j)
            line = adsk.fusion.SketchLine.cast(curve.sketchEntity)
            if line:
                s = line.startSketchPoint.geometry
                e = line.endSketchPoint.geometry
                msg += "\n  [%5.2f,%5.2f]->[%5.2f,%5.2f]" % (
                    s.x, s.y,e.x,e.y 
                )
        return msg

    def getIntersections(self, line, curves):
        points = adsk.core.ObjectCollection.create()
        for i in range(curves.count):
            curve = curves.item(i).geometry
            pnts = line.intersectWithCurve(curve)
            for j in range(pnts.count):
                c = pnts.item(j)
                for k in range(points.count):
                    e = points.item(k)
                    if e.x == c.x and e.y == c.y and e.z == c.z:
                        c = None
                        break
                if c: 
                    points.add(c)

        return points

    def findIntersections(self, centroid, profile ):
        global _ui
        sketch = adsk.fusion.Sketch.cast(profile.parentSketch)
        profile = adsk.fusion.Profile.cast(profile)
        outerPoint = profile.boundingBox.maxPoint
        pCurves = profile.profileLoops.item(0).profileCurves
        line = adsk.core.Line3D.create(outerPoint, centroid)
        points = self.getIntersections(line, pCurves)
        if points.count == 0:
            outerPoint = profile.boundingBox.minPoint
            line = adsk.core.Line3D.create(outerPoint, centroid)
            points = self.getIntersections(line, pCurves)

        # don't beleive it is possible in euclidian space for not found second time
        return points

    def midPoint(self, pnt0, pnt1):
        ax = (pnt0.x + pnt1.x) / 2
        ay = (pnt0.y + pnt1.y) / 2
        az = (pnt0.z + pnt1.z) / 2
    
        return adsk.core.Point3D.create(ax, ay, az)

    def findInsidePoint(self, profile ):
        # best guesss at point inside
        centroid = profile.areaProperties().centroid
        
        for i in range(10):
            points = self.findIntersections(centroid, profile)
            # if number of intersecting points is odd, the centroid is inside
            if (points.count % 2) == 1:
                return centroid
            #else guess at new centroid
            centroid = self.midPoint(points.item(0), points.item(1))
            
        return None

    def containsProfile(self, outer, profile):
        # return outer.boundingBox.intersects(profile.boundingBox)
        points = None
        insidePnt = self.findInsidePoint( profile)
        if insidePnt:
            points = self.findIntersections(insidePnt, outer)
            # if number of intersecting points is odd, the profile is inside
            if (points.count % 2) == 1:
                return True

        return False

    def offset(self, sketch, ploop, dist ):
        # curves = adsk.core.ObjectCollection.create()
        # for curve in ploop.profileCurves:
        #     curves.add(curve)
        sketch = adsk.fusion.Sketch.cast(sketch)
        dirPoint = ploop.parentProfile.areaProperties().centroid
        offsetCurves = sketch.offset(ploop.profileCurves, dirPoint, dist)
        return offsetCurves

    def notify(self, args):
        global _app, _ui
        try:
            cmdArgs = adsk.core.CommandEventArgs.cast(args)
            inputs = cmdArgs.command.commandInputs
            selector = inputs.itemById("profile_select")
            selectedProfile = adsk.fusion.Profile.cast(selector.selection(0).entity)
            sketch = adsk.fusion.Sketch.cast(_app.activeEditObject)

            if _ui:
                msg = ""

                for i in range(sketch.profiles.count):
                    profile = sketch.profiles.item(i)
                    if  profile != selectedProfile and self.containsProfile(selectedProfile, profile):
                        msg += self.pLoopDetails(profile.profileLoops.item(0))                

                _ui.messageBox('Profiles:%s' % msg) 
 
        except:
            _ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))


# Event handler that reacts to when the command is destroyed. This terminates the script.            
class MyCommandDestroyHandler(adsk.core.CommandEventHandler):
    def __init__(self):
        super().__init__()

    def notify(self, args):
        global _app, _ui
        try:
            # When the command is done, terminate the script
            # This will release all globals which will remove all event handlers
            cmdArgs = adsk.core.CommandEventArgs.cast(args)

            adsk.terminate()
        except:
            _ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))


# Event handler that creates my Command.
class MyCommandCreatedHandler(adsk.core.CommandCreatedEventHandler):
    def __init__(self):
        super().__init__()
    def notify(self, args):
        global _app, _ui
        try:
            # Get the command that was created.
            cmd = adsk.core.Command.cast(args.command)

            # Connect to the command destroyed event.
            onDestroy = MyCommandDestroyHandler()
            cmd.destroy.add(onDestroy)
            _handlers.append(onDestroy)

            # Connect to the execute event.           
            onExecute = MyCommandExecuteHandler()
            cmd.execute.add(onExecute)
            _handlers.append(onExecute) 

            onSelect = MySelectHandler()
            cmd.select.add(onSelect)
            _handlers.append(onSelect) 

            # # Connect to the input changed event.           
            # onInputChanged = MyCommandInputChangedHandler()
            # cmd.inputChanged.add(onInputChanged)
            # _handlers.append(onInputChanged)    

            # onExecutePreview = MyCommandExecutePreviewHandler()
            # cmd.executePreview.add(onExecutePreview)
            # _handlers.append(onExecutePreview)        

            # Get the CommandInputs collection associated with the command.
            inputs = cmd.commandInputs

            # Create a selection input.
            selectionInput = inputs.addSelectionInput('profile_select', 'Profile', 'Profile to Kern')
            selectionInput.addSelectionFilter(adsk.core.SelectionCommandInput.Profiles)
            selectionInput.setSelectionLimits(1,1)


        except:
            _ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))


def run(context):
    try:
        global _app, _ui
        _app = adsk.core.Application.get()
        _ui = _app.userInterface

        # Get the existing command definition or create it if it doesn't already exist.
        cmdDef = _ui.commandDefinitions.itemById('cmdKernProfile')
        if not cmdDef:
            cmdDef = _ui.commandDefinitions.addButtonDefinition('cmdKernProfile', 
                                                                'Kern Selected Profile',
                                                                'My Second command')

        # Connect to the command created event.
        onCommandCreated = MyCommandCreatedHandler()
        cmdDef.commandCreated.add(onCommandCreated)
        _handlers.append(onCommandCreated)

        # Execute the command definition.
        cmdDef.execute()

        # Prevent this module from being terminated when the script returns.
        adsk.autoTerminate(False)
    except:
        if _ui:
            _ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))