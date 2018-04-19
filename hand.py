

import cv2                              
import numpy as np   
import copy
from required import *
import serial
import sys

#cap = cv2.VideoCapture(1)                #creating camera object
#cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
#cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 780)
cv2.namedWindow('distanceTransform',cv2.WINDOW_NORMAL)
cv2.namedWindow('drawing',cv2.WINDOW_NORMAL) 
cv2.namedWindow('input',cv2.WINDOW_NORMAL)
cv2.namedWindow('fingerContour',cv2.WINDOW_NORMAL)
cv2.namedWindow('drawingContour',cv2.WINDOW_NORMAL)
cv2.namedWindow('final',cv2.WINDOW_NORMAL)


kernel = np.ones((9,9),np.uint8)
HS = None    
RS = None
HandLength = None
font = cv2.FONT_HERSHEY_SIMPLEX

while( True ):
	try:

		#imr = '../Dataset/hand2.jpg'
		imr = '../Dataset/3.jpg'
		img = cv2.imread(imr,1) 
		h, w = img.shape[:2]
		#ret , 
		#img = cap.read()                       #reading the frames
		gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
		blur = cv2.GaussianBlur(gray,(5,5),0)
		ret,handThresh = cv2.threshold(blur,0,255,cv2.THRESH_BINARY_INV+cv2.THRESH_OTSU)

		handThreshCopy = np.copy(handThresh)
		_ ,contours, hierarchy = cv2.findContours(handThresh,cv2.RETR_TREE,cv2.CHAIN_APPROX_SIMPLE)
		cnt = maxCont(contours)
		hull = cv2.convexHull(cnt)
		drawing = np.zeros(img.shape,np.uint8)
		drawingContour = np.zeros(img.shape,np.uint8)
		cv2.drawContours(drawingContour,[cnt],0,(255,255,0),-2)
		cv2.imshow('drawingContour',drawingContour)

		grayImg = cv2.cvtColor(drawingContour, cv2.COLOR_BGR2GRAY)
		blurimg = cv2.GaussianBlur(grayImg,(5,5),0)
		ret,handThresh = cv2.threshold(blurimg,0,255,cv2.THRESH_BINARY+cv2.THRESH_OTSU)
		handThreshCopy = np.copy(handThresh)
		_ ,contours, hierarchy = cv2.findContours(handThresh,cv2.RETR_TREE,cv2.CHAIN_APPROX_SIMPLE)
		cnt = maxCont(contours)
		hull = cv2.convexHull(cnt)


		dist, labels = cv2.distanceTransformWithLabels(handThresh, cv2.DIST_L2, 5)
		inRange = .50
		dtHand = np.uint8(dist*inRange)


		cv2.imshow('distanceTransform',dtHand)

		segmentMask = np.uint8(dist)
		wristMask = np.copy(segmentMask)
		segmentMask[:] = 255
		wristMask[:]=0
		ret1,palmPointThresh = cv2.threshold(dtHand,dtHand.max() - 15*inRange,dtHand.max(),cv2.THRESH_BINARY)
		im1 , palm , hierarchyPalm = cv2.findContours(palmPointThresh, cv2.RETR_TREE,cv2.CHAIN_APPROX_SIMPLE)
		palmCentre  = contourCenter(palm)
		print ("PalmCentre = "+str(palmCentre))
		radius = cv2.pointPolygonTest(cnt,palmCentre,True)
		if(radius < 400 and radius > 0):	
			#segmentation of finger and wrist line 
			cv2.circle(img,palmCentre,int(radius*1.38),[0,255,0],2)
			cv2.circle(img,palmCentre,int(radius*1.8),[0,255,0],2)
			cv2.circle(segmentMask,palmCentre,int(radius*1.9),[0,0,0],-1)
			cv2.circle(wristMask,palmCentre,int(radius*2.2),[255,255,255],-1)  #outer circle
			cv2.circle(wristMask,palmCentre,int(radius*1.9),[0,0,0],-1) #inner circle
			wristMask = cv2.bitwise_and(handThreshCopy , handThreshCopy , mask = wristMask)
			#wristMask = cv2.erode(wristMask,kernel,iterations = 15)
			segmentedFinger = cv2.bitwise_and(handThreshCopy , handThreshCopy ,mask = segmentMask)
			cv2.imshow("fingerContour",segmentedFinger)
			
			#masking
			im2 , fingerContour , hierarchyFinger = cv2.findContours(segmentedFinger , cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
			im3 , wristCountors , hierarchyWrist = cv2.findContours(wristMask , cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
			wristCountor = maxCont(wristCountors)

			#center for wrist
			momCont = cv2.moments(wristCountor,False)
			cx = int(momCont['m10']/momCont['m00'])
			cy = int(momCont['m01']/momCont['m00'])
			wristCenter = (cx,cy)

			#slope of hand
			HS = np.arctan((palmCentre[1]-wristCenter[1])/((1.0)*(palmCentre[0]-wristCenter[0])))
			HS = (180/3.14)*HS
			
			#Drawing functions
			cv2.line(img,wristCenter,palmCentre,[0,0,0],2)
			cv2.circle(img,wristCenter,5,[255,255,255],-1)
			cv2.circle(img,palmCentre,5,[255,255,255],-1)
			cv2.drawContours(drawing,[wristCountor],0,(255,255,0),2)
			cv2.drawContours(drawing,[cnt],0,(0,255,0),2)
			cv2.drawContours(drawing,[hull],0,(0,0,255),2)
			cv2.drawContours(drawing,[palm[0]],0,(0,255,0),2)
			cv2.imshow("final",drawing)
		
		hull = cv2.convexHull(cnt,returnPoints = False)
		defects = cv2.convexityDefects(cnt,hull)
		i=0

		fingerTip = []
		for i in range(defects.shape[0]):
			s,e,f,d = defects[i,0]
			start = tuple(cnt[s][0])	
			end = tuple(cnt[e][0])
			far = tuple(cnt[f][0])
			if distAB(start , end) > 70:
				cv2.line(img,start,end,[0,255,0],2)                
				cv2.circle(img,start,10,[0,0,255],-1)
				fingerTip.append(start)

		drawing1 = np.copy(segmentMask)
		drawing1[:]=0
			           
		#finger Contour Identification
		K = "1"
		centerList = []
		contourList = []
		print ("Slope = " +str(HS))

		for j in fingerContour:
			area = cv2.contourArea(j)
			if area > 500 and area < 100000 :
				FingerCont = cv2.moments(j,False)
				cx = int(FingerCont['m10']/FingerCont['m00'])
				cy = int(FingerCont['m01']/FingerCont['m00'])
				center = (cx ,cy)
				contourList.append(j)
				centerList.append(center)
				cv2.putText(drawing1,K,center, font, 2,(255,255,255),2,cv2.LINE_AA)
				cv2.drawContours(drawing1,[j],0,(200,5,62),2)
				K = K + "1"

		#pairedPoints[][0] is starting point and pairedPoints[][1] is center point  
		pairedPoints = pairFingerTipAndCenter(fingerTip, centerList ,contourList)
		print ("Paired points = " , pairedPoints)


		cv2.imshow('input',drawing1)

		allPaired = pairAll(pairedPoints, wristCenter[0])
		for I in allPaired:
			(x,y) = ((int)(I[2][0]),(int)(I[2][1]))
			cv2.circle(img,I[1],5,[255,255,255],-1)
			cv2.circle(img,I[0],5,[255,255,255],-1)
			cv2.circle(img,(x,y),5,[255,255,255],-1)

		print ("All paired :" , allPaired)

		print ("Radius = ", radius)

		
		cv2.imshow('drawing',img)
		
		endAndRoot = findRoot(pairedPoints , palmCentre , radius*1.35)

		counter = 0
		for P in endAndRoot:
			point = ((int)(endAndRoot[counter][1][0]) , (int)(endAndRoot[counter][1][1]))
			cv2.line(img,endAndRoot[counter][0],point,[0,0,0],2)
			counter = counter + 1
		print ("counter = "+str(counter))
		

		#HandLength = distAB(endAndRoot[0][1] , endAndRoot[3][1])
		HandLength =  cv2.pointPolygonTest(wristCountor,wristCenter,True)
		print ("HandLength = " +str(HandLength) )



		#fingerPropeties[0] for each countour and 1 RC , 2 TC , 3 distance
		fingerProperties = []
		counter = 0
		for I in fingerContour:
			area = cv2.contourArea(I)
			print ("area = "+str(area))
			print ("len = "+str(len(endAndRoot)))
			if area > 500 and area < 100000 and counter < 5:
				prop = calcProp(I,HS,endAndRoot , palmCentre ,counter ,HandLength ,img)
				counter = counter + 1
				fingerProperties.append(prop)
				
		if (counter >= 0):
			fingerProbability = calcProbSum(fingerProperties)
			facN = math.factorial(counter)
			fac5mn = math.factorial(5 - counter)
			comb = 120/(fac5mn*facN)
		
		fingers = ('Little', 'Ring' , 'Middle' , 'Index' , 'Thumb')
		#fingers = ('Ring')
		print (fingerProbability)

		for I in fingerProbability:
			maJ = 0
			maxc = 0
			counter = 0
			for J in I :
				if maJ < J :
					maJ = J
					maxc = counter
				counter = counter + 1
			cv2.putText(img,fingers[maxc],centerList[maxc],font,2,(255,225,25),2,cv2.LINE_AA)
		
		print ("fingerProbability = ", fingerProbability)
		 


		k = cv2.waitKey(10) & 0xFF
		if k == ord('q'):
			break


	except  : 
		PrintException()
		print ("\n\n\n\n\n\n")
		k = cv2.waitKey(10) & 0xFF
		if k == ord('q'):
			sys.exit()   
		pass

cv2.destroyAllWindows()


