C    Program to print effect in head-dep-flux budget of Modified McAda Wasiolek Model
c    Superposition version (including La Cienega Springs in GHB package)
c    Includes effects to Rio Grande, tributaries, and La Cienega Springs
C                                                                       00013000
C      CBC FILE FROM RIV PACKAGE (Rio Grande and Tribs) UNIT# 7         READ
C      CBC FILE FROM GHB PACKAGE (La Cienega Springs)   UNIT# 8         READ
C      OUTPUT                                           UNIT# 6         WRITE
C                                                                       00014000
      CHARACTER*30 EXPL
	character*3 mo(12)
C
      CHARACTER*30 RVBUDFIL,GHBUDFIL
c      CHARACTER*30 SSBUDFIL
      CHARACTER*30 OUTFIL
C
      DIMENSION BUFF(10000),TEXT(4),KSP(3100,2),LRC(50,3),BUD(50,3100),
     +BUDSUM(4,3100),IYR(3100),GHBSUM(3100),GHB(50,3100),BUFFg(10000),
     +LRCg(50,3)

C                                                                       00016000
      INRV=7
      INGH=8

      IOUT=6
	mo(1)='jan'
	mo(2)='feb'
	mo(3)='mar'
	mo(4)='apr'
	mo(5)='may'
	mo(6)='jun'
	mo(7)='jul'
	mo(8)='aug'
	mo(9)='sep'
	mo(10)='oct'
	mo(11)='nov'
	mo(12)='dec'

C
      Write(*,*)' SFMODFLX.FOR  Postprocessor' 
      Write(*,*)'  Modified McAda Wasiolek Model, Superposition version'
      Write(*,*)' Summarizes effects to Rio Grande, tributaries,'
      Write(*,*)'  and La Cienega Springs'
      Write(*,*)' INPUTS:                '                                                       00013000
      Write(*,*)'  MODFLOW .FLX OUTPUT FILE FROM RIV PACKAGE' 
      Write(*,*)'      (Rio Grande and Tribs)'
      Write(*,*)'  MODFLOW .FLX OUTPUT FILE FROM GHB PACKAGE'
      Write(*,*)'     (La Cienega Springs)'
      Write(*,*)' OUTPUT: A summary file named by the user.'       
	                            

  99   WRITE(*,100)
 100  FORMAT(/,' Enter Name of Unformatted RIV FLX File
     1')
      READ(*,101) RVBUDFIL
 101  FORMAT(A30)
      OPEN(INRV,FILE=RVBUDFIL,FORM='UNFORMATTED',STATUS='OLD',ERR=111)
	goto 112
111	write(0,124)
124	format(' ERROR: file does not exist, try again')
	goto 99
112	continue
C
 199   WRITE(*,300)
 300  FORMAT(/,' Enter Name of Unformatted GHB FLX File
     1')
      READ(*,101) GHBUDFIL

      OPEN(INGH,FILE=GHBUDFIL,FORM='UNFORMATTED',STATUS='OLD',ERR=311)
	goto 312
311	write(0,124)

	goto 199
312	continue
      WRITE(*,120)
 120  FORMAT(/,' Enter File Name for Output  ')
      READ(*,121) OUTFIL
 121  FORMAT(A30)
      OPEN(IOUT,FILE=OUTFIL,STATUS='UNKNOWN')
	iyro= 1988

C
      II=0
      DO 381 K=1,4
      DO 380 J=1,3097
      BUDSUM(K,J)=0.
      GHBSUM(J)=0.
  380 CONTINUE
  381 CONTINUE
	do 481 k=1,50
	do 481 j=1,3097
	ghb(k,j)=0.0
481	bud(k,j)=0.0
C                                                                       00019000
c cycle through time steps
      DO 1 J=1,3097
      JJ=J
       JJ2=1
c READ HEADER LINES
      READ(INRV,END=1000) KSTP,KPER,TEXT,NCOL,NROW,NLAY                 00022000
      READ(INGH,END=1000) KSTP,KPER,TEXT,NCOL,NROW,NLAY                 00022000

C                                                                       00027000
C  READ FLOW RATES                                                      00028000
      NODES=NCOL*NROW*NLAY                                              00029000
      READ(INRV) (BUFF(I),I=1,NODES)                                    00030000
      READ(INGH) (BUFFg(I),I=1,NODES)                                   00030000
c      write(iout,223)(buff(i),i=1,nodes)
c223	format(27(e10.2,2x))
c	stop
C                                                                       00031000
C  LOAD NONZERO RATES INTO ARRAY BUD    
      CALL FILL(NCOL,NROW,NLAY,BUFFg,IOUT,LRCg,ghb,jj,IIg,2)                                00033000                                              00032000
      CALL FILL(NCOL,NROW,NLAY,BUFF,IOUT,LRC,BUD,JJ,II,JJ2)     
c      write(*,*)' iig = ',iig
c      write(*,*)' ii = ',ii                                             00033000

C
 333  CONTINUE
C
      KSP(J,1)=KSTP
      KSP(J,2)=KPER
C
1     CONTINUE                                                          00034000
C                                                                       00035000
C  END OF DATA                                                          00036000
C
C FORMAT TABLES
C
 1000 JJ=JJ-1
	write(*,*)' number of timesteps in file = ',jj,' +1'
      X=JJ/12.                                                        00037000
      LOOP=X
      X=(X-LOOP)+0.001
      LEFT=X*12.
      IF (LEFT .GT. 0) THEN
      LOOP=LOOP+1
      ELSE
      LEFT=12
      END IF
C
C     SUM RIVER NODE BUDGETS BY STREAM SYSTEM
C
      DO 390 J=1,II
      IF((LRC(J,2).EQ.9).AND.(LRC(J,3).GT.13)) GO TO 384
      IF((LRC(J,2).LT.13).AND.(LRC(J,3).GT.21)) GO TO 384
      IF(LRC(J,3).GT.18) GO TO 386
      M=3
      GO TO 388
  384 M=1
      GO TO 388
  386 M=2
  388 DO 389 K=1,JJ

      BUDSUM(M,K)=BUDSUM(M,K)+BUD(J,K)
      BUDSUM(4,K)=BUDSUM(4,K)+BUD(J,K)
  389 CONTINUE
  390 CONTINUE

C    SUM GHB NODES
	DO 490 J=1,IIg
	DO 490 K=1,JJ
490	GHBSUM(K)=GHBSUM(K)+GHB(J,K)


C
C FIRST PRINT BUDGET,  L=1
      EXPL=' PUMPAGE EFFECT ON RIV. BUDGET'
      DO 391 K=1,JJ
	lyr=int(k/12.-.05)
      IYR(K)=iyro+lyr
  391 CONTINUE
C
  399 DO 400 I=1,LOOP
      I1=(I-1)*12+1
      I2=I*12
      IF (I .EQ. LOOP) I2=(I-1)*12+LEFT
      I3=(I1+I2)/2




      WRITE (IOUT,201)EXPL
c	Write (IOUT,202)iyr(I1)
      WRITE (IOUT,205) iyr(I1),(mo(J),J=1,12)
      WRITE (IOUT,*)' LAY ROW COL'
      WRITE (IOUT,206)
  201 FORMAT (1H1,A30,20X,'CFS (+ INDICATES REDUCED STREAM FLOW)')
  202 FORMAT(' Year ',i6)
  205 FORMAT (1H+,129(1H_),//,'YEAR: ',i4,2x,
     +12(6X,A3,3x))
  206 FORMAT (1H+,129(1H_)/)
C
      DO 382 J=1,II
  382 WRITE (IOUT,209) (LRC(J,K),K=1,3),(BUD(J,K),K=I1,I2)
  209 FORMAT (1H ,3I4,12F12.6)
      WRITE(IOUT,211) (BUDSUM(1,K),K=I1,I2)
  211 FORMAT(1H0,'  R POJOAQUE',12F12.6)
      WRITE(IOUT,212) (BUDSUM(2,K),K=I1,I2)
  212 FORMAT(1H0,'   R TESUQUE',12F12.6)
      WRITE(IOUT,213) (BUDSUM(3,K),K=I1,I2)
  213 FORMAT(1H0,'  RIO GRANDE',12F12.6)
      WRITE(IOUT,214) (BUDSUM(4,K),K=I1,I2)
  214 FORMAT(1H0,'  RIV  TOTAL',12F12.6)
      WRITE(IOUT,215) (GHBSUM(K),K=I1,I2)
  215 FORMAT(1H0,'  LC SPRINGS',12F12.6)	
	write(iout,*)
	write(iout,*)
  400 CONTINUE

      STOP
      END                                                               00038000
C
      SUBROUTINE FILL(NCOL,NROW,NLAY,BUFF,IOUT,LRC,BUD,JJ,II,JJ2)                          00039000
      DIMENSION BUFF(NCOL,NROW,NLAY),LRC(50,3),BUD(50,200)
C
C  FIND NODES WITH NON-ZERO RIVER BUDGETS. NEEDED ONLY FOR 1ST TIME
      IF ( JJ2 .EQ. 1) THEN
      III=0
      IS=9
      IX=17
      JS=14
      JX=25
      else if(jj2.eq.2)then
	III=0
	IS=28
	IX=35
	JS=10
	JX=20
	end if

      K=1
      DO 2 KK=1,2
      DO 200 I=IS,IX                                                     00042000
      DO 200 J=JS,JX                                                    00043000
      IF(BUFF(J,I,K).EQ.0.) GO TO 200                                   00044000
      III=III+1
      II=III
      BUD(II,JJ)=BUFF(J,I,K)
      BUFF(J,I,K)=0.0
      LRC(II,1)=K
      LRC(II,2)=I
      LRC(II,3)=J
c	write(iout,224)ii,lrc(ii,1),lrc(ii,2),lrc(ii,3),bud(ii,jj)
c224	format(4I4,f12.4)
  200 CONTINUE                                                          00047000
      IS=1
      IX=25
      JS=1
      JX=18
    2 CONTINUE
c	stop
c      ELSE
C  IF ALREADY KNOW WHICH NODES, DON'T NEED TO FIND THEM AGAIN
c      JJJ=JJ+JJ2-1
c      DO 300 I=1,II
c  300 BUD(I,JJJ)=BUFF(LRC(I,3),LRC(I,2),LRC(I,1))
c     END IF
   99 RETURN                                                            00048000
      END                                                               00049000

