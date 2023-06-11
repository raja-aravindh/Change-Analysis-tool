import arcpy
from arcpy.sa import *
import numpy

class Toolbox(object):
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Change Analysis"
        self.alias = "Change Analysis"

        # List of tool classes associated with this toolbox
        self.tools = [ChangeAnalysis]


class ChangeAnalysis(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Change Analysis"
        self.description = """Computes the changes between two rasters and generates a new raster incorporating those changes which can be customized using various parameters"""
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""
        param0 = arcpy.Parameter(
            displayName="From Raster",
            name="fromRaster",
            datatype="GPRasterLayer",
            parameterType="Required",
            direction="Input")
        
        param1 = arcpy.Parameter(
            displayName="To Raster",
            name="toRaster",
            datatype="GPRasterLayer",
            parameterType="Required",
            direction="Input")

        param2 = arcpy.Parameter(
            displayName="Output Raster",
            name="outputRaster",
            datatype="DERasterDataset",
            parameterType="Required",
            direction="Output")
        
        param3 = arcpy.Parameter(
            displayName="Filter Method",
            name="filterMethod",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param3.filter.type = "ValueList"
        param3.filter.list = ["All", "Changed only", "Unchanged only"]
        param3.value = param3.filter.list[0]

        param4 = arcpy.Parameter(
            displayName="Classname Field (From Raster)",
            name="fromClassNameField",
            datatype="Field",
            parameterType="Required",
            direction="Input")
        param4.filter.list = ['Text', 'Long']
        param4.parameterDependencies = [param0.name]

        param5 = arcpy.Parameter(
            displayName="Classname Field (To Raster)",
            name="toClassNameField",
            datatype="Field",
            parameterType="Required",
            direction="Input")
        param5.filter.list = ['Text', 'Long']
        param5.parameterDependencies = [param1.name]

        param6 = arcpy.Parameter(
            displayName="From Class(es)",
            name="fromClass",
            parameterType="Required",
            direction="Input",
            multiValue=True)
        param6.filter.type = "ValueList"
        param6.controlCLSID = "{38C34610-C7F7-11D5-A693-0008C711C8C1}"

        param7 = arcpy.Parameter(
            displayName="To Class(es)",
            name="toClass",
            parameterType="Required",
            direction="Input",
            multiValue=True)
        param7.filter.type = "ValueList"
        param7.controlCLSID = "{38C34610-C7F7-11D5-A693-0008C711C8C1}"
        
        params = [param0, param1, param2, param3, param4, param5, param6, param7]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        if arcpy.CheckExtension("Spatial") == "Available":
            return True
        else:
            return False

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        if parameters[0].value:
            try:
                with arcpy.da.SearchCursor(parameters[0].valueAsText, "value") as cursor:
                    pass
                    
            except:
                parameters[4].altered = ""
                parameters[4].enabled = False
            else:
                del cursor
                parameters[4].enabled = True
                fields = arcpy.Describe(parameters[0].valueAsText).fields
                for field in fields:
                    if field.name.lower() == "value":
                        parameters[4].value = field.name                    
                    elif field.type == "String":
                        if ("class" in field.name.lower() or "name" in field.name.lower()):
                            parameters[4].value = field.name
                        if not parameters[4].altered:
                            parameters[4].value = field.name

        if parameters[1].value and not parameters[5].altered:
            fields = arcpy.Describe(parameters[1].valueAsText).fields
            for field in fields:
                if field.name.lower() == "value":
                    parameters[5].value = field.name
                elif field.type == "String":
                    parameters[4].enabled = True
                    if ("class" in field.name.lower() or "name" in field.name.lower()):
                        parameters[5].value = field.name
                    if not parameters[5].altered:
                        parameters[5].value = field.name
                
        if (parameters[4].value):
            parameters[6].enabled = True
            parameters[6].filter.list = [row[0] for row in arcpy.da.SearchCursor(
                                                parameters[0].valueAsText,
                                                parameters[4].valueAsText)]

        else:
            parameters[6].enabled = False

        if (parameters[5].value):
            parameters[7].enabled = True
            parameters[7].filter.list = [row[0] for row in arcpy.da.SearchCursor(
                                                parameters[1].valueAsText,
                                                parameters[5].valueAsText)]
        else:
            parameters[7].enabled = False
        
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        
        message = "Input Raster does not have Attribute Table."
        
        if parameters[0].value:
            try:
                cursor = arcpy.da.SearchCursor(parameters[0].valueAsText, "value")
            except:
                parameters[4].enabled = False
            else:
                parameters[4].enabled = True
                del cursor

        if parameters[1].value:
            try:
                cursor = arcpy.da.SearchCursor(parameters[1].valueAsText, "value")
            except:
                parameters[5].enabled = False
                parameters[1].setErrorMessage(message)
            else:
                parameters[5].enabled = True
                del cursor
            
        if parameters[4].value and parameters[5].value:
            if ((parameters[4].valueAsText.lower() == "value" or parameters[5].valueAsText.lower() == "value")
            and parameters[4].valueAsText.lower() != parameters[5].valueAsText.lower()):
                message = "Field type of Classname Fields of From and To Rasters should be the same." 
                parameters[4].setErrorMessage(message)
                parameters[5].setErrorMessage(message)

        return

    def execute(self, parameters, messages):
        """The source code of the tool."""

        arcpy.env.overwriteOutput = True

        fromRaster = parameters[0].valueAsText
        toRaster = parameters[1].valueAsText
        outputRaster = parameters[2].valueAsText
        filterMethod = parameters[3].valueAsText
        classNameField_from = parameters[4].valueAsText
        classNameField_to = parameters[5].valueAsText
        fromClassNames = parameters[6].valueAsText
        toClassNames = parameters[7].valueAsText

        #function to filter input rasters based on parameters
        def filterClause(fromValue, toValue, returnType):
            if filterMethod == "All":
                if returnType == "String":
                    filterClause = "None"
                else:
                    filterClause = True

            elif filterMethod == "Changed only":
                filterClause = (fromValue-toValue != 0)
            else:
                filterClause = (fromValue-toValue == 0)
            filterClause *= (fromValue * toValue != 0)
            return filterClause

        #funtion to convert raster to numpy array
        def rasterToNumpy(rasterObj, classValueList):
            numpyArray = arcpy.RasterToNumPyArray(rasterObj,nodata_to_value=0)
            uniqueValues = numpy.unique(numpyArray)
            for value in uniqueValues:
                if value not in classValueList:
                    numpyArray[numpyArray == value] = 0
            return numpyArray

        #function to add new fields to output raster
        def addFields(outputRaster, classNameLists, inputClassField):
            if classNameField_from.lower() == "value":
                fieldType = "LONG"
            else:
                fieldType = "TEXT"
            #Add required fields to output raster table
            arcpy.management.AddField(outRaster, "Class_name", "TEXT")
            arcpy.management.AddField(outRaster, "From_class", "{}".format(fieldType))
            arcpy.management.AddField(outRaster, "To_class", "{}".format(fieldType))
            arcpy.management.AddField(outRaster, "Area_sq_km", "DOUBLE", 15, field_alias="Area (sq.km)")

            #Calculate field values for above added fields
            with arcpy.da.UpdateCursor(outputRaster, ["Class_name", "From_class", "To_class", "Count", "Area_sq_km"]) as cursor:
                n = 0
                for row in cursor:
                    row[0] = classNameLists[n][0]
                    row[1] = classNameLists[n][1]
                    row[2] = classNameLists[n][2]
                    row[4] = row[3] * cellSize[0] * cellSize[1] / (1000 * 1000)
                    cursor.updateRow(row)
                    n += 1        
            
        fromClassNameList = fromClassNames.split(";")
        toClassNameList = toClassNames.split(";") 

        #Create a Dictionary & populate with Values & Names from From & To Rasters
        fromRasterList = [(row[0],row[1]) for row in arcpy.da.SearchCursor(
                                            fromRaster, ["Value", classNameField_from])]
        toRasterList   = [(row[0],row[1]) for row in arcpy.da.SearchCursor(
                                            toRaster, ["Value", classNameField_to])]

        fromClassValueList = [tpl[0] for tpl in fromRasterList if str(tpl[1]) in fromClassNameList]
        toClassValueList = [tpl[0] for tpl in toRasterList if str(tpl[1]) in toClassNameList]

        #Create a list to hold the ClassNames of output, From & To rasters
        classNameLists = []
        for ftuple in fromRasterList:
            arcpy.AddMessage(type(ftuple[1]))
            if str(ftuple[1]) in fromClassNameList:
                classNameLists += [["{} to {}".format(ftuple[1], ttuple[1]), ftuple[1], ttuple[1]]
                          for ttuple in toRasterList
                          if (filterClause(ftuple[0], ttuple[0], "String")
                          and str(ttuple[1]) in toClassNameList)]

        # Get input Raster properties
        fromRasObj = arcpy.Raster(fromRaster)
        toRasObj = arcpy.Raster(toRaster)
        lowerLeft = arcpy.Point(fromRasObj.extent.XMin,fromRasObj.extent.YMin)
        cellSize = [fromRasObj.meanCellWidth, fromRasObj.meanCellHeight]
        arcpy.env.outputCoordinateSystem = fromRasObj

        # Convert input Rasters to numpy arrays
        fromRasArray = rasterToNumpy(fromRasObj, fromClassValueList)
        toRasArray = rasterToNumpy(toRasObj, toClassValueList)

        outNumpyArray = numpy.add(fromRasArray * (max(toClassValueList) + 1),           toRasArray, 
        where = (filterClause(fromRasArray, toRasArray, "Boolean")
                                 ))

        outUniqueValues = list(numpy.unique(outNumpyArray))
        outClassValues = range(len(outUniqueValues))
        for value in outUniqueValues:
            newValueIndex = outUniqueValues.index(value)
            outNumpyArray[outNumpyArray == value] = outClassValues.index(newValueIndex)


        arcpy.AddMessage(numpy.unique(outNumpyArray))

        # Convert numpy array to output Raster
        outRaster = arcpy.NumPyArrayToRaster(outNumpyArray,lowerLeft,
                                             cellSize[0],cellSize[1],value_to_nodata=0)

        
        outRaster.save(r"{}".format(outputRaster))

        addFields(outputRaster, classNameLists, classNameField_from)

        return

    def postExecute(self, parameters):
        """This method takes place after outputs are processed and
        added to the display."""
        return




